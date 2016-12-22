# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class to manage container engines in which the environments are created."""

from importlib import import_module
import abc
from contextlib import contextmanager
import logging

class Container(object):
    """
    Base class for installing and managing container engines.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, resource, config):
        """
        Class constructor

        Parameters
        ----------
        resource : object
            Instance of a Resource sub-class
        config : dictionary
            Configuration parameters for the container.
        """

        # Merge runtime config parameters into resource config.
        resource._config.update(config)

        self._resource = resource
        self._command_buffer = [] # Each element is a dictionary in the
                                  # form {command=[], env={}}
        self._env = {}
        self._lgr = logging.getLogger('repronim.container')

    @staticmethod
    @contextmanager
    def factory(resource, config = {}):
        """
        Factory method for creating the appropriate Container sub-class.

        Parameters
        ----------
        resource : object
            Platform sub-class instance
        config : dictionary
            Configuration parameters for the container.

        Returns
        -------
        Container sub-class instance.
        """
        container_name = resource.get_config('container').replace('-', '')
        class_name = container_name.capitalize() + 'Container'
        module = import_module('repronim.container.' + container_name)
        instance = getattr(module, class_name)(resource, config)
        instance.create()
        yield instance
        instance.execute_command_buffer()

    @abc.abstractmethod
    def create(self):
        """
        Create a container instance.
        """
        return

    @abc.abstractmethod
    def execute_command(self, command, env):
        """
        Execute the given command in the container.

        Parameters
        ----------
        command : string or list
            Shell command string or list of command tokens to send to the
            container to execute.

        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call

        Returns
        -------
        list
            List of STDOUT lines from the container.
        """
        return

    def add_command(self, command, env=None):
        """
        Add a command to the command buffer so that all commands can be
        run at once in a batch submit to the container.

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
        Send all the commands in the command buffer to the container for
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

    def get_config(self, key):
        """
        Convenience method to access the configuration parameters in the
        resource object.

        Parameters
        ----------
        key : string
            Identifier of configuration setting.

        Returns
        -------
        Value of configuration parameter indexed by the key.
        """
        return self._resource.get_config(key)

    def set_config(self, key, value):
        """
        Convenience method to set a configuration parameter in the
        resource object.

        Parameters
        ----------
        key : string
            Identifier of configuration setting.
        value : string
            Value of the configuration setting.

        Returns
        -------
        """
        self._resource.set_config(key, value)