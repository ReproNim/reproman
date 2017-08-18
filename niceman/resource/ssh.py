# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of a SSH connection."""

import attr
import re
from os import chmod
from os.path import join
from appdirs import AppDirs

import logging
lgr = logging.getLogger('niceman.resource.ssh')

from .base import Resource, attrib
import niceman.support.sshconnector2 # Needed for test patching to work.
from ..ui import ui
from ..utils import assure_dir
from ..dochelpers import exc_str
from ..support.exceptions import ResourceError
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

    def connect(self):
        """
        Open a connection to the environment resource.
        """
        self._ssh = niceman.support.sshconnector2.SSHConnector2(self.host,
            port=self.port,
            key_filename=self.key_filename,
            username=self.user,
            password=self.password, # TODO: We can use password authentication, but how to securely save the password?
        )

    def create(self):
        """
        Create an EC2 instance.

        Returns
        -------
        dict : config and state parameters to capture in the inventory file
        """
        self.id = self.host # TODO: The id should be a niceman-created unique identifier.
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

    def execute_command(self, ssh, command, env=None):
        """
        Execute the given command in the environment.

        Parameters
        ----------
        ssh : SSHConnector2 instance
            SSH connection object
        command : list
            Shell command string or list of command tokens to send to the
            environment to execute.
        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call
        """
        command_env = self.get_updated_env(env)

        # if command_env:
            # TODO: might not work - not tested it
            # command = ['export %s=%s;' % k for k in command_env.items()] + command

        # If a command fails, a CommandError exception will be thrown.
        for i, line in enumerate(ssh(" ".join(command))):
            lgr.debug("exec#%i: %s", i, line.rstrip())

    def execute_command_buffer(self):
        """
        Send all the commands in the command buffer to the environment for
        execution.
        """
        with niceman.support.sshconnector2.SSHConnector2(self.host,
            port=self.port,
            key_filename=self.key_filename,
            username=self.user,
            password=self.password) as ssh:
            for command in self._command_buffer:
                lgr.info("Running command '%s'", command['command'])
                self.execute_command(ssh, command['command'], command['env'])

    def login(self):
        """
        Log into remote environment and get the command line
        """
        lgr.debug("Opening TTY connection via SSH.")
        ssh = SSHClient(self.host,
            username=self.user,
            password=self.password,
            private_key=self.key_filename,
            port=self.port)
        ssh.interactive_shell(self.user)
