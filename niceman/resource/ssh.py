# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Resource sub-class to provide management of a SSH connection."""

import attr
import uuid
from pipes import quote

import logging
lgr = logging.getLogger('niceman.resource.ssh')

from .base import Resource, attrib
from ..support.starcluster.sshutils import SSHClient


@attr.s
class SSH(Resource):

    # Generic properties of any Resource
    name = attr.ib()

    # Configurable options for each "instance"
    host = attrib(doc="DNS or IP address of server")
    port = attrib(default=22,
        doc="Port to connect to on remote host")
    key_filename = attrib(default=None,
        doc="Path to SSH private key file matched with AWS key name parameter")
    user = attrib(default=None,
        doc="Username to use to log into remote environment")
    password = attrib(default=None,
        doc="Password to use to log into remote environment")

    id = attr.ib(default=None)  # EC2 instance ID

    type = attr.ib(default='ssh')  # Resource type

    # Current instance properties, to be set by us, not augmented by user
    status = attr.ib(default=None)
    _ssh = attr.ib(default=None)

    def connect(self):
        """
        Open a connection to the environment resource.
        """
        self._ssh = SSHClient(
            self.host,
            username=self.user,
            password=self.password,
            private_key=self.key_filename,
            port=int(self.port)
        )

    def create(self):
        """
        Register the SSH connection to the niceman inventory registry.

        Returns
        -------
        dict : config and state parameters to capture in the inventory file
        """
        if not self.id:
            self.id = str(uuid.uuid4())
        self.status = 'N/A'
        return {
            'id': self.id,
            'status': self.status,
            'host': self.host,
            'user': self.user,
            'port': self.port,
            'key_filename': self.key_filename,
        }

    def delete(self):
        self._ssh = None
        return

    def start(self):
        return

    def stop(self):
        return

    def get_session(self, pty=False, shared=None):
        """
        Log into remote environment and get the command line
        """
        if not self._ssh:
            self.connect()

        return (PTYSSHSession if pty else SSHSession)(
            ssh=self._ssh
        )

# Alias SSH class so that it can be discovered by the ResourceManager.
@attr.s
class Ssh(SSH):
    pass


from niceman.resource.session import POSIXSession

@attr.s
class SSHSession(POSIXSession):
    ssh = attr.ib()

    def _execute_command(self, command, env=None, cwd=None):
        """
        Execute the given command in the environment.

        Parameters
        ----------
        command : list
            Shell command string or list of command tokens to send to the
            environment to execute.
        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call
        """
        # TODO -- command_env is not used etc...
        # command_env = self.get_updated_env(env)

        if cwd:
            raise NotImplementedError("implement cwd support")
        # if command_env:
            # TODO: might not work - not tested it
            # command = ['export %s=%s;' % k for k in command_env.items()] + command

        # If a command fails, a CommandError exception will be thrown.
        escaped_command = ' '.join(quote(s) for s in command)
        for i, line in enumerate(self.ssh.execute(escaped_command)):
            lgr.debug("exec#%i: %s", i, line.rstrip())

    def exists(self, path):
        """Return if file exists"""
        return self.ssh.path_exists(path)

    def copy_to(self, src_path, dest_path='.'):
        """Take file on the local file system and copy over into the session
        """
        self.ssh.put([src_path], remotepath=dest_path)

    def copy_from(self, src_path, dest_path='.'):
        """Retrieve a file from the remote system
        """
        self.ssh.get(src_path, localpath=dest_path)

    def chmod(self, mode, remote_path):
        """Set the mode of a remote path
        """
        self.ssh.chmod(mode, remote_path)

    def chown(self, uid, gid, remote_path):
        """Set the user and group of a path
        """
        self.ssh.chown(uid, gid, remote_path)

    def read(self, path, mode='r'):
        """Return content of a file"""
        return self.ssh.get_remote_file_lines(path)

    def mkdir(self, path, mode="0755"):
        """Create a directory. Create parent directories if non-existent
        """
        self.ssh.makedirs(path, int(mode, 8))

    def isdir(self, path):
        """Return True if path is pointing to a directory
        """
        return self.ssh.isdir(path)


@attr.s
class PTYSSHSession(SSHSession):
    """Interactive SSH Session"""

    def open(self):
        lgr.debug("Opening TTY connection via SSH.")
        assert self.ssh, "We should create or connect to remote server first"
        self.ssh.interactive_shell(self.ssh._username)

    def close(self):
        # XXX ?
        pass