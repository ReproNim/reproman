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
import paramiko
import os

import logging
lgr = logging.getLogger('niceman.resource.ssh')

from .base import Resource
from ..utils import attrib
from niceman.dochelpers import borrowdoc
from niceman.resource.session import Session
from niceman import utils
from ..support.exceptions import CommandError


@attr.s
class SSH(Resource):

    # Generic properties of any Resource
    name = attrib(default=attr.NOTHING)

    # Configurable options for each "instance"
    host = attrib(doc="DNS or IP address of server")
    port = attrib(default=22,
        doc="Port to connect to on remote host")
    key_filename = attrib(
        doc="Path to SSH private key file matched with AWS key name parameter")
    user = attrib(
        doc="Username to use to log into remote environment")
    password = attrib(
        doc="Password to use to log into remote environment")

    id = attrib()  # EC2 instance ID

    type = attrib(default='ssh')  # Resource type

    # Current instance properties, to be set by us, not augmented by user
    status = attrib()
    _ssh = attrib()

    def connect(self):
        """Open a connection to the environment resource.
        """
        self._ssh = paramiko.SSHClient()
        self._ssh.load_system_host_keys()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh.connect(
            self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            key_filename=self.key_filename
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

        self._ssh.resource = self
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
    ssh = attrib(default=attr.NOTHING)

    @borrowdoc(Session)
    def _execute_command(self, command, env=None, cwd=None):
        # TODO -- command_env is not used etc...
        # command_env = self.get_updated_env(env)
        if env:
            raise NotImplementedError("passing env variables to execution")

        if cwd:
            raise NotImplementedError("implement cwd support")
        # if command_env:
            # TODO: might not work - not tested it
            # command = ['export %s=%s;' % k for k in command_env.items()] + command

        escaped_command = ' '.join(quote(s) for s in command)
        stdin, stdout, stderr = self.ssh.exec_command(escaped_command)
        exit_code = stdout.channel.recv_exit_status()
        stdout = utils.to_unicode(stdout.read(), "utf-8")
        stderr = utils.to_unicode(stderr.read(), "utf-8")

        if exit_code not in [0, None]:
            msg = "Failed to run %r. Exit code=%d. out=%s err=%s" \
                % (command, exit_code, stdout, stderr)
            raise CommandError(str(command), msg, exit_code, stdout, stderr)
        else:
            lgr.log(8, "Finished running %r with status %s", command,
                exit_code)

        return (stdout, stderr)

    @borrowdoc(Session)
    def put(self, src_path, dest_path, uid=-1, gid=-1):
        dest_dir, dest_basename = os.path.split(dest_path)
        if not self.exists(dest_dir):
            self.mkdir(dest_dir, parents=True)
        sftp = self.ssh.open_sftp()
        sftp.put(src_path, dest_path)
        sftp.close()

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid)

    @borrowdoc(Session)
    def get(self, src_path, dest_path, uid=-1, gid=-1):
        dest_dir, dest_basename = os.path.split(dest_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        sftp = self.ssh.open_sftp()
        sftp.get(src_path, dest_path)
        sftp.close()

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid, remote=False)


@attr.s
class PTYSSHSession(SSHSession):
    """Interactive SSH Session"""

    @borrowdoc(Session)
    def open(self):
        lgr.debug("Opening TTY connection via SSH.")
        assert self.ssh, "We should create or connect to remote server first"
        self.interactive_shell()

    @borrowdoc(Session)
    def close(self):
        # XXX ?
        pass

    def interactive_shell(self):
        """Open an interactive TTY shell.
        """
        ssh_cmdline = ["ssh",
                       "-i", self.ssh.resource.key_filename,
                       "-p", "{0:d}".format(self.ssh.resource.port),
                       '%s@%s' % (self.ssh.resource.user,
                            self.ssh.resource.host)]
        os.execlp("ssh", *ssh_cmdline)
