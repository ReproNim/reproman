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
import invoke
import uuid
from fabric import Connection
import os

import logging
lgr = logging.getLogger('niceman.resource.ssh')

from .base import Resource
from ..utils import attrib
from niceman.dochelpers import borrowdoc
from niceman.resource.session import Session
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

    id = attrib()  # EC2 instance ID

    type = attrib(default='ssh')  # Resource type

    # Current instance properties, to be set by us, not augmented by user
    status = attrib()
    _connection = attrib()

    def connect(self, password=None):
        """Open a connection to the environment resource.

        Parameters
        ----------
        password : string
            We don't allow users to pass in a password via the command line
            but do allow tests to authenticate by passing a password as
            a parameter to this method.
        """
        self._connection = Connection(
            self.host,
            user=self.user,
            port=self.port,
            connect_kwargs={
                'key_filename': self.key_filename,
                'password': password
            }
        )
        self._connection.open()

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
        self._connection = None
        return

    def start(self):
        return

    def stop(self):
        return

    def get_session(self, pty=False, shared=None):
        """
        Log into remote environment and get the command line
        """
        if not self._connection:
            self.connect()

        return (PTYSSHSession if pty else SSHSession)(
            connection=self._connection
        )


# Alias SSH class so that it can be discovered by the ResourceManager.
@attr.s
class Ssh(SSH):
    pass


from niceman.resource.session import POSIXSession


@attr.s
class SSHSession(POSIXSession):
    connection = attrib(default=attr.NOTHING)

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

        try:
            result = self.connection.run(' '.join(command), hide=True)
        except invoke.exceptions.UnexpectedExit as e:
            result = e.result

        if result.return_code not in [0, None]:
            msg = "Failed to run %r. Exit code=%d. out=%s err=%s" \
                % (command, result.return_code, result.stdout, result.stderr)
            raise CommandError(str(command), msg, result.return_code,
                result.stdout, result.stderr)
        else:
            lgr.log(8, "Finished running %r with status %s", command,
                result.return_code)

        return (result.stdout, result.stderr)

    @borrowdoc(Session)
    def put(self, src_path, dest_path, uid=-1, gid=-1):
        dest_dir, _ = os.path.split(dest_path)
        if not self.exists(dest_dir):
            self.mkdir(dest_dir, parents=True)
        self.connection.put(src_path, dest_path)

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid)

    @borrowdoc(Session)
    def get(self, src_path, dest_path, uid=-1, gid=-1):
        dest_dir, _ = os.path.split(dest_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        self.connection.get(src_path, dest_path)

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid, remote=False)

    @borrowdoc(POSIXSession)
    def exists_command(self, path):
        return ['bash', '-c', '"test', '-e', path, '&&', 'echo', 'Found"']

    @borrowdoc(POSIXSession)
    def isdir_command(self, path):
        return ['bash', '-c', '"test', '-d', path, '&&', 'echo', 'Found"']

    @borrowdoc(POSIXSession)
    def get_mtime_command(self, path):
        return ['python', '-c',
            '"import os, sys; print(os.path.getmtime(sys.argv[1]))"',
            path]


@attr.s
class PTYSSHSession(SSHSession):
    """Interactive SSH Session"""

    @borrowdoc(Session)
    def open(self):
        lgr.debug("Opening TTY connection via SSH.")
        self.interactive_shell()

    @borrowdoc(Session)
    def close(self):
        # XXX ?
        pass

    def interactive_shell(self):
        """Open an interactive TTY shell.
        """
        self.connection.run('/bin/bash', pty=True)
        print('Exited terminal session.')
