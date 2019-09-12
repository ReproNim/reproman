# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Resource sub-class to provide management of a SSH connection."""

import attr
import getpass
import uuid
from ..log import LoggerHelper
# OPT: invoke, fabric and paramiko is imported at the point of use

import logging
lgr = logging.getLogger('reproman.resource.ssh')
# Add Paramiko logging for log levels below DEBUG
if lgr.getEffectiveLevel() < logging.DEBUG:
    LoggerHelper("paramiko").get_initialized_logger()

from .base import Resource
from ..utils import attrib
from ..utils import command_as_string
from reproman.dochelpers import borrowdoc
from reproman.resource.session import Session
from ..support.exceptions import CommandError

# Silence CryptographyDeprecationWarning's.
# TODO: We should bump the required paramiko version and drop the code below
# once paramiko cuts a release that includes
# <https://github.com/paramiko/paramiko/pull/1379>.
import warnings
warnings.filterwarnings(action="ignore", module=".*paramiko.*")


@attr.s
class SSH(Resource):

    # Generic properties of any Resource
    name = attrib(default=attr.NOTHING)

    # Configurable options for each "instance"
    host = attrib(default=attr.NOTHING, doc="DNS or IP address of server")
    port = attrib(
        doc="Port to connect to on remote host")
    key_filename = attrib(
        doc="Path to SSH private key file")
    user = attrib(
        doc="Username to use to log into remote environment")

    id = attrib()

    type = attrib(default='ssh')  # Resource type

    # Current instance properties, to be set by us, not augmented by user
    status = attrib()
    _connection = attrib()

    def _connection_open(self):
        try:
            self.status = "CONNECTING"
            self._connection.open()
            self.status = "ONLINE"
        except:
            self.status = "CONNECTION ERROR"
            raise

    def connect(self, password=None):
        """Open a connection to the environment resource.

        Parameters
        ----------
        password : string
            We don't allow users to pass in a password via the command line
            but do allow tests to authenticate by passing a password as
            a parameter to this method.
        """
        # Convert key_filename to a list
        # See: https://github.com/ReproNim/reproman/commit/3807f1287c39ea2393bae26803e6da8122ac5cff
        from fabric import Connection
        from paramiko import AuthenticationException
        connect_kwargs = {}
        if self.key_filename:
            connect_kwargs["key_filename"] = [self.key_filename]
        if password:
            connect_kwargs["password"] = password

        self._connection = Connection(
            self.host,
            user=self.user,
            port=self.port,
            connect_kwargs=connect_kwargs
        )

        if self.key_filename:
            auth = self.key_filename
        elif password is None:
            auth = "SSH config"
        else:
            auth = "password"

        lgr.debug("SSH connecting to %s@%s:%s, authenticating with %s",
                  self._connection.user, self._connection.host,
                  self._connection.port,  # Fabric defaults to 22.
                  auth)
        try:
            self._connection_open()
        except AuthenticationException:
            password = getpass.getpass(
                prompt="Password for {}: ".format(self.name))
            self._connection = Connection(
                self.host,
                user=self.user,
                port=self.port,
                connect_kwargs={'password': password}
            )
            self._connection_open()

    def create(self):
        """
        Register the SSH connection to the reproman inventory registry.

        Yields
        -------
        dict : config parameters to capture in the inventory file
        """
        if not self.id:
            self.id = str(uuid.uuid4())
        self.status = 'N/A'
        yield {
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
        # Not a SSH feature
        raise NotImplementedError

    def stop(self):
        # Not a SSH feature
        raise NotImplementedError

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


from reproman.resource.session import POSIXSession


@attr.s
class SSHSession(POSIXSession):
    connection = attrib(default=attr.NOTHING)

    @borrowdoc(Session)
    def _execute_command(self, command, env=None, cwd=None, with_shell=False,
                        handle_permission_denied=True):
        # TODO -- command_env is not used etc...
        # command_env = self.get_updated_env(env)
        from invoke.exceptions import UnexpectedExit
        command = self._prefix_command(command_as_string(command), env=env,
                                        cwd=cwd, with_shell=with_shell)
        try:
            result = self.connection.run(command, hide=True)
        except UnexpectedExit as e:
            if 'permission denied' in e.result.stderr.lower() and handle_permission_denied:
                # Issue warning once
                if not getattr(self, '_use_sudo_warning', False):
                    lgr.warning(
                        "Permission is denied for %s. From now on will use 'sudo' "
                        "in such cases",
                        command
                    )
                    self._use_sudo_warning = True
                return self._execute_command(
                    "sudo " + command,  # there was command_as_string
                    env=env,
                    cwd=cwd,
                    handle_permission_denied=False
                )
            else:
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
        dest_path = self._prepare_dest_path(src_path, dest_path, local=False)
        self.connection.put(src_path, dest_path)

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid)

    @borrowdoc(Session)
    def get(self, src_path, dest_path=None, uid=-1, gid=-1):
        dest_path = self._prepare_dest_path(src_path, dest_path)
        self.connection.get(src_path, dest_path)

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid, remote=False)


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
