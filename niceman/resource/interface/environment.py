# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class interface definition for environment resources."""

import abc

import logging
lgr = logging.getLogger('niceman.resource.interface.environment')

class Environment(object):
    """
    Abstract class that defines the interface for an environment.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def poll_status(self):
        """
        Poll the backend for info on the environment. Updates the ResourceConfig.
        """
        return

    @abc.abstractmethod
    def create(self, image_id):
        """
        Create a running environment.

        Parameters
        ----------
        image_id : string
            Identifier of the base image to use when creating the environment.
        """
        return

    @abc.abstractmethod
    def delete(self):
        """
        Remove this environment from the backend.
        """
        return

    @abc.abstractmethod
    def connect(self):
        """
        Connect to an existing environment resource.
        """
        return

    @abc.abstractmethod
    def execute_command(self, command, env):
        """
        Execute the given command in the environment.

        Parameters
        ----------
        command : string or list
            Shell command string or list of command tokens to send to the
            environment to execute.

        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call

        Returns
        -------
        list
            List of STDOUT lines from the environment.
        """
        return

    def add_command(self, command, env=None):
        """
        Add a command to the command buffer so that all commands can be
        run at once in a batch submit to the environment.

        Parameters
        ----------
        command : string or list
            Command string or list of command string tokens.

        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call
        """
        if not hasattr(self, '_command_buffer'):
            self._command_buffer = [] # Each element is a dictionary in the
                                      # form {command=[], env={}}
        self._command_buffer.append({'command':command, 'env':env})

    def execute_command_buffer(self):
        """
        Send all the commands in the command buffer to the environment for
        execution.
        """
        for command in self._command_buffer:
            lgr.debug("Running command '%s'", command['command'])
            self.execute_command(command['command'], command['env'])

    def set_envvar(self, var, value):
        """
        Save an evironment variable for inclusion in the environment

        Parameters
        ----------
        var : string
            Variable name
        value : string
            Variable value

        Returns
        -------

        """
        if not hasattr(self, '_env'):
            self._env = {}

        self._env[var] = value

    def get_updated_env(self, custom_env):
        """
        Returns an env dictionary with additional or replaced values.

        Parameters
        ----------
        custom_env : dict
            Environment variables to merge into the existing list of declared
            environment variables stored in self._env

        Returns
        -------
        dictionary
        """
        if hasattr(self, '_env'):
            merged_env = self._env.copy()
            if custom_env:
                merged_env.update(custom_env)
            return merged_env

        return custom_env