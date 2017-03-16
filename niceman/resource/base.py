# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to manage compute resources."""

from importlib import import_module
import abc

import logging
lgr = logging.getLogger('niceman.resource.base')

from ..support.exceptions import MissingConfigError

# Enumerate the defined resource types available.
VALID_RESOURCE_TYPES = [
    'docker-container',
    'aws-ec2',
    'shell'
]


class Resource(object):
    """
    Base class for creating and managing compute resources.
    """

    __metaclass__ = abc.ABCMeta

    def __repr__(self):
        return 'Resource({})'.format(self.name)

    @staticmethod
    def factory(config):
        """
        Factory method for creating the appropriate Container sub-class.

        Parameters
        ----------
        resource_config : ResourceConfig object
            Configuration parameters for the resource.

        Returns
        -------
        Resource sub-class instance.
        """
        if 'type' not in config:
            raise MissingConfigError("Resource 'type' parameter missing for resource.")

        module_name = '_'.join(config['type'].split('-'))
        class_name = ''.join([token.capitalize() for token in config['type'].split('-')])
        module = import_module('niceman.resource.{}'.format(module_name))
        instance = getattr(module, class_name)(**config)
        return instance

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

    @classmethod
    def _generate_id(cls):
        import uuid
        # just a random uuid for now, TODO: think if we somehow could
        # fingerprint it so to later be able to decide if it is 'ours'? ;)
        return str(uuid.uuid1())

