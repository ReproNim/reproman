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

import logging
lgr = logging.getLogger('niceman.resource.ssh')

from .base import Resource, attrib
from ..support.starcluster.sshutils import SSHClient


@attr.s
class Ssh(Resource):

    # Generic properties of any Resource
    name = attr.ib()

    # Configurable options for each "instance"
    host = attrib(default=None,
        doc="DNS or IP address of server.")
    port = attrib(default=22,
        doc="Port to connect to on remote host.")
    key_filename = attrib(default=None,
        doc="Path to SSH private key file matched with AWS key name parameter.") # SSH private key filename on local machine.
    user = attrib(default=None,
        doc="Username to use to log into remote environment.")
    password = attrib(default=None,
        doc="Password to use to log into remote environment.")

    id = attr.ib(default=None)  # EC2 instance ID

    type = attr.ib(default='ssh')  # Resource type

    # Current instance properties, to be set by us, not augmented by user
    status = attr.ib(default=None)
    _ssh = attr.ib(default=None)

    def connect(self):
        """
        Open a connection to the environment resource.
        """
        self._ssh = SSHClient(self.host,
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
        return

    def start(self):
        return

    def stop(self):
        return

    def get_session(self, pty=False, shared=None):
        """
        Log into remote environment and get the command line
        """
        assert self._ssh, "We should create or connect to remote server first"

        if pty and shared is not None and not shared:
            lgr.warning("Cannot do non-shared pty session for ssh server yet")

        return (PtySshSession if pty else SshSession)(
            ssh=self._ssh
        )


from niceman.resource.session import POSIXSession

@attr.s
class SshSession(POSIXSession):
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
        for i, line in enumerate(self.ssh.execute(" ".join(command))):
            lgr.debug("exec#%i: %s", i, line.rstrip())

@attr.s
class PtySshSession(SshSession):
    """Interactive SSH Session"""

    def open(self):
        lgr.debug("Opening TTY connection via SSH.")
        assert self.ssh, "We should create or connect to remote server first"
        self.ssh.interactive_shell(self.ssh._username)

    def close(self):
        # XXX ?
        pass