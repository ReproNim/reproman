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
import socket
import paramiko
import os
import getpass
from binascii import hexlify
from paramiko.py3compat import input

import logging
lgr = logging.getLogger('niceman.resource.ssh')

from .base import Resource
from ..utils import attrib
from niceman.dochelpers import borrowdoc
from niceman.resource.session import Session
from niceman import utils
from ..support.exceptions import CommandError, SSHError
from ..support import paramiko_interactive


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
    _transport = attrib()
    _channel = attrib()

    def connect(self, password=None):
        """Open a connection to the environment resource.

        Parameters
        ----------
        password : string
            We don't allow users to pass in a password via the command line
            but do allow tests to authenticate by passing a password as
            a parameter to this method.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, int(self.port)))

        self._transport = paramiko.Transport(sock)
        self._transport.start_client()

        try:
            keys = paramiko.util.load_host_keys(
                os.path.expanduser("~/.ssh/known_hosts")
            )
        except IOError:
            try:
                keys = paramiko.util.load_host_keys(
                    os.path.expanduser("~/ssh/known_hosts")
                )
            except IOError:
                lgr.debug("Unable to open host keys file")
                keys = {}

        key = self._transport.get_remote_server_key()
        if self.host not in keys:
            lgr.debug("Unknown host key!")
        elif key.get_name() not in keys[self.host]:
            lgr.debug("Unknown host key!")
        elif keys[self.host][key.get_name()] != key:
            raise SSHError("Host key has changed!!!")
        else:
            lgr.debug("Host key valid.")

        if self.user == "":
            default_username = getpass.getuser()
            username = input("Username [%s]: " % default_username)
            if len(username) == 0:
                self.user = default_username

        self._agent_auth()
        if not self._transport.is_authenticated() and self.key_filename:
            try:
                key = paramiko.RSAKey.from_private_key_file(self.key_filename)
            except paramiko.PasswordRequiredException:
                rsa_password = getpass.getpass("RSA key password: ")
                key = paramiko.RSAKey.from_private_key_file(self.key_filename,
                    rsa_password)
            self._transport.auth_publickey(self.user, key)
        if not self._transport.is_authenticated() and password:
            self._transport.auth_password(self.user, password)
        if not self._transport.is_authenticated():
            self._manual_auth()
        if not self._transport.is_authenticated():
            self._transport.close()
            raise SSHError("Authentication failed")

    def _agent_auth(self):
        """
        Attempt to authenticate to the given transport using any of the private
        keys available from an SSH agent.
        """
        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        if len(agent_keys) == 0:
            return

        for key in agent_keys:
            lgr.debug("Trying ssh-agent key %s" % hexlify(key.get_fingerprint()))
            try:
                self._transport.auth_publickey(self.user, key)
                lgr.debug("ssh-agent key %s succeeded!"
                    % hexlify(key.get_fingerprint()))
                return
            except paramiko.SSHException:
                lgr.debug("ssh-agent key %s failed!"
                    % hexlify(key.get_fingerprint()))

    def _manual_auth(self):
        """
        Prompt user for authorization method and information.
        """
        default_auth = "p"
        auth = input(
            "Auth by (p)assword, (r)sa key, or (d)ss key? [%s] " % default_auth
        )
        if len(auth) == 0:
            auth = default_auth

        if auth == "r":
            default_path = os.path.join(os.environ["HOME"], ".ssh", "id_rsa")
            path = input("RSA key [%s]: " % default_path)
            if len(path) == 0:
                path = default_path
            try:
                key = paramiko.RSAKey.from_private_key_file(path)
            except paramiko.PasswordRequiredException:
                password = getpass.getpass("RSA key password: ")
                key = paramiko.RSAKey.from_private_key_file(path, password)
            self._transport.auth_publickey(self.user, key)
        elif auth == "d":
            default_path = os.path.join(os.environ["HOME"], ".ssh", "id_dsa")
            path = input("DSS key [%s]: " % default_path)
            if len(path) == 0:
                path = default_path
            try:
                key = paramiko.DSSKey.from_private_key_file(path)
            except paramiko.PasswordRequiredException:
                password = getpass.getpass("DSS key password: ")
                key = paramiko.DSSKey.from_private_key_file(path, password)
            self._transport.auth_publickey(self.user, key)
        else:
            password = getpass.getpass("Password for %s@%s: " % (self.user, self.host))
            self._transport.auth_password(self.user, password)

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
        if not self._transport:
            self.connect()

        return (PTYSSHSession if pty else SSHSession)(
            transport=self._transport
        )


# Alias SSH class so that it can be discovered by the ResourceManager.
@attr.s
class Ssh(SSH):
    pass


from niceman.resource.session import POSIXSession

@attr.s
class SSHSession(POSIXSession):
    transport = attrib(default=attr.NOTHING)

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

        channel = self.transport.open_session()
        channel.exec_command(' '.join(command))
        exit_code = channel.recv_exit_status()
        stdout = utils.to_unicode(channel.makefile("rb").read(), "utf-8")
        stderr = utils.to_unicode(channel.makefile_stderr("rb").read(), "utf-8")

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
        sftp = paramiko.SFTPClient.from_transport(self.transport)
        sftp.put(src_path, dest_path)
        sftp.close()

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid)

    @borrowdoc(Session)
    def get(self, src_path, dest_path, uid=-1, gid=-1):
        dest_dir, dest_basename = os.path.split(dest_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        sftp = paramiko.SFTPClient.from_transport(self.transport)
        sftp.get(src_path, dest_path)
        sftp.close()

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
        assert self.transport, "We should create or connect to remote server first"

        # TODO: Can we make these values dynamic based on the user's screen size?
        self.term = 'screen'
        self.cols = 80
        self.lines = 24
        self.timeout = 30

        self.interactive_shell()

    @borrowdoc(Session)
    def close(self):
        # XXX ?
        pass

    def interactive_shell(self):
        """Open an interactive TTY shell.
        """
        channel = self.transport.open_session()
        channel.get_pty()
        channel.invoke_shell()
        paramiko_interactive.interactive_shell(channel)
        channel.close()
        self.transport.close()
