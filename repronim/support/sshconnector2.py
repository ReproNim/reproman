# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Interface to an ssh connection."""

import logging
import paramiko
import sys

lgr = logging.getLogger('repronim.sshconnector2')


class SSHConnector2(object):
    """
    Manage and use an SSH connection.
    """

    # TODO: eventually we might need to have
    #  - X forwarding
    #     see e.g. http://stackoverflow.com/a/12876252 on how to do with Paramiko
    #  - local port forwarding... to channel VNC session -- not sure if
    #     could be done with paramiko.  there is sshtunnel Python module though
    #     and some homebrewed solutions on top of paramiko:
    #     http://stackoverflow.com/a/12106387
    #  Get back to reprozip and check what they did?
    def __init__(self, host, username='ubuntu', key_filename=None):
        """
        Collect the connection parameters and create client object.

        Parameters
        ----------
        host : string
            host to connect to.
        username : string
            username for remote account logging into
        key_filename : string
            path of ssh private key
        """
        self._host = host
        self._username = username
        self._key_filename = key_filename

        self._client = paramiko.SSHClient()
        # TODO: make configurable
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def __enter__(self):
        """
        Method handler for entering a context

        Returns
        -------
        Instance of SSHConnection2 class
        """
        try:
            self._client.connect(self._host, username=self._username,
                key_filename=self._key_filename)
        except paramiko.AuthenticationException:
            lgr.error("SSH authentication failed when connecting to %s", self._host)
            sys.exit(1)

        lgr.debug("Successfully connected via SSH to host %s", self._host)

        return self

    def __exit__(self, *args):
        """
        Method handler for context exit

        Returns
        -------
        """
        self._client.close()
        lgr.debug("Closed SSH connection to host %s", self._host)

    def __call__(self, cmd):
        """
        Executes a command on the remote server.

        Parameters
        ----------
        cmd : str
          command to run on the remote server

        Returns
        -------
        tuple of str
          stdout, stderr of the command run.
        """
        # try:
        stdout_lines = []

        lgr.debug("Sending command '%s' to host %s", cmd, self._host)
        stdin, stdout, stderr = self._client.exec_command(cmd)

        # Close stdin and trigger the command on the remote server.
        stdin.close()

        # Wait for command to complete. This is a blocking call.
        exit_status = stdout.channel.recv_exit_status()
        lgr.debug("Command '%s' completed, exit status = %i", cmd, exit_status)

        for line in stdout.read().splitlines():
            stdout_lines.append(line)

        # TODO:  decide on either throw an exception or return exit status
        # We must not just swallow/warn about it
        if exit_status != 0:
            lgr.warning("Command '%s' failed, exit status = %i", cmd, exit_status)

        return stdout_lines
