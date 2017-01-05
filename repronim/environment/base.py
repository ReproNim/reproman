# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class to manage environment engines in which the environments are created."""

import abc

from ..resource import Resource


class Environment(Resource):
    """
    Base class for installing and managing computational environments.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        """
        Class constructor

        Parameters
        ----------
        config : dictionary
            Configuration parameters for the environment.
        """
        super(Environment, self).__init__(config)

        self._command_buffer = [] # Each element is a dictionary in the
                                  # form {command=[], env={}}
        self._env = {}

    @abc.abstractmethod
    def create(self, name, image_id):
        """
        Create a running environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to be created.
        image_id : string
            Identifier of the image to use when creating the environment.
        """
        return

    @abc.abstractmethod
    def connect(self, name=None):
        """
        Connect to an existing environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to connect to.
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

    def get_resource_client(self):
        """
        Retrieve the resource object for the client for the backend that is
        hosting the environment.

        Returns
        -------
        Instance of a Client class
        """
        resource_client = self.get_config('resource_client')
        config_path = self.get_config('config_path')
        return Resource.factory(resource_client, config_path=config_path)

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
        self._command_buffer.append({'command':command, 'env':env})

    def execute_command_buffer(self):
        """
        Send all the commands in the command buffer to the environment for
        execution.
        """
        for command in self._command_buffer:
            self._lgr.debug("Running command '%s'", command['command'])
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
        self._env[var] = value

    def get_updated_env(self, custom_env):
        """
        Returns an env dictionary with additional or replaced values.

        Parameters
        ----------
        custom_env : dict
            Enviroment variables to merge into the existing list of declared
            environment variables stored in self._env

        Returns
        -------
        dictionary
        """
        merged_env = self._env.copy()
        if custom_env:
            merged_env.update(custom_env)
        return merged_env