# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to manage compute resources."""

import attr
from importlib import import_module
import abc

import logging
lgr = logging.getLogger('niceman.resource.base')

import yaml
from os.path import basename
from os.path import dirname
from os.path import join as opj
from glob import glob
import os.path

from ..config import ConfigManager
from ..dochelpers import exc_str
from ..support.exceptions import ResourceError
from ..support.exceptions import MissingConfigError, MissingConfigFileError
from ..ui import ui

def attrib(*args, **kwargs):
    """
    Extend the attrs decorator to include a doc metadata element.
    """
    doc = kwargs.get('doc')
    metadata = kwargs.get('metadata', {})
    if doc:
        metadata['doc'] = doc
        del kwargs['doc']
    if metadata:
        kwargs['metadata'] = metadata
    return attr.ib(*args, **kwargs)

class ResourceManager(object):
    """
    Class to help manage resources.
    """

    __metaclass__ = abc.ABCMeta

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


        type_ = config['type']
        module_name = '_'.join(type_.split('-'))
        class_name = ''.join([token.capitalize() for token in type_.split('-')])
        try:
            module = import_module('niceman.resource.{}'.format(module_name))
        except ImportError as exc:
            raise ResourceError(
                "Failed to import resource: {}.  Known ones are: {}".format(
                    exc_str(exc),
                    ', '.join(ResourceManager._discover_types()))
            )
        instance = getattr(module, class_name)(**config)
        return instance

    # TODO: Following methods might better be in their own class
    @staticmethod
    def _discover_types():
        l = []
        for f in glob(opj(dirname(__file__), '*.py')):
            f_ = basename(f)
            if f_ in ('base.py',) or f_.startswith('_'):
                continue
            l.append(f_[:-3])
        return sorted(l)

    @staticmethod
    def get_resource_info(config_path, name, id_=None, type_=None):
        """
        Sort through the parameters supplied by the user at the command line and then
        request the ones that are missing that are needed to find the config and
        inventory files and then build the config dictionary needed to connect
        to the environment.

        Parameters
        ----------
        config_path : string
            Path to the niceman.cfg file.
        name : string
            Name of the resource
        id_ : string
            The identifier of the resource as assigned to it by the backend
        type_ : string
            Type of the resource module used to manage the name, e.g.
            "docker_container".

        Returns
        -------
        config : dict
            The config settings for the name.
        inventory : dict
            Inventory of all the managed resources and their configurations.
        """

        # Get name configuration for this name if it exists
        # We get the config from inventory first if it exists and then
        # overlay the default config settings from repronim.cfg
        cm = ResourceManager.get_config_manager(config_path)
        inventory_path = cm.getpath('general', 'inventory_file')
        inventory = ResourceManager.get_inventory(inventory_path)
        # XXX: ATM mixes creation with querying existing resources.
        #      IMHO (yoh) should just query, and leave creation to a dedicated function
        # TODO: query could be done via ID
        # TODO: check that if both name and id provided -- they are as it is in
        #       inventory
        # TODO:  if no name or id provided, then fail since this function
        #        is not created to return a list of resources for a given type ATM

        vald_resource_types = [t.replace("_", "-") for t in ResourceManager._discover_types()]

        if name in inventory:
            # XXX so what is our convention here on SMTH-SMTH defining the type?
            config = dict(cm.items(inventory[name]['type'].split('-')[0]))
            config.update(inventory[name])
        elif type_ and type_ in vald_resource_types:
            config = dict(cm.items(type_.split('-')[0]))
        else:
            type_ = ui.question(
                "Enter a resource type",
                # TODO: decision on type of a container, if needed
                # needs to be done outside, and should be configurable
                # or follow some heuristic (e.g. if name starts with a
                # known type, e.g. docker-
                default="docker-container"
            )
            config = {}
            if type_ not in vald_resource_types:
                raise MissingConfigError(
                    "Resource type '{}' is not valid".format(type_))

        # Overwrite config settings with those from the command line.
        config['name'] = name
        if type_:
            config['type'] = type_
        if id_:
            config['id'] = id_

        return config, inventory

    @staticmethod
    def get_config_manager(config_path=None):
        """
        Returns the information stored in the niceman.cfg file.

        Parameters
        ----------
        config_path : string
            Path to the niceman.cfg file. (optional)

        Returns
        -------
        cm : ConfigManager object
            Information stored in the niceman.cfg file.
        """
        def get_cm(config_path):
            if config_path:
                cm = ConfigManager([config_path], False)
            else:
                cm = ConfigManager()
            return cm

        # Look for a niceman.cfg file in the local directory if none given.
        if not config_path and os.path.isfile('niceman.cfg'):
            config_path = 'niceman.cfg'
        cm = get_cm(config_path=config_path)
        if not config_path and len(cm._sections) == 1:
            config = ui.question("Enter a config file", default="niceman.cfg")
            cm = get_cm(config_path=config)
        if len(cm._sections) == 1:
            raise MissingConfigFileError(
                "Unable to locate config file: {}".format(config_path))

        return cm

    @staticmethod
    def get_inventory(inventory_path):
        """
        Returns a dictionary containing the config information for all resources
        created by niceman.

        Parameters
        ----------
        inventory_path : string
            Path to the inventory file which is declared in the niceman.cfg file.

        Returns
        -------
        inventory : dict
            Hash whose key is resource name and value is the config settings for
            the resource.
        """
        if not inventory_path:
            raise MissingConfigError(
                "No resource inventory file declared in niceman.cfg")

        # Create inventory file if it does not exist.
        if not os.path.isfile(inventory_path):
            lgr.info("Creating resources inventory file %s", inventory_path)
            # initiate empty inventory
            ResourceManager.set_inventory({'_path': inventory_path})

        with open(inventory_path, 'r') as fp:
            inventory = yaml.safe_load(fp)

        inventory['_path'] = inventory_path
        return inventory

    @staticmethod
    def set_inventory(inventory):
        """
        Save the resource inventory to a file. The location of the file is
        declared in the niceman.cfg file.

        Parameters
        ----------
        inventory : dict
            Hash whose key is the name of the resource and value is the config
            settings of the resource.
        """

        # Operate on a copy so there is no side-effect of modifying original
        # inventory
        inventory = inventory.copy()
        inventory_path = inventory.pop('_path')

        for key in list(inventory):  # go through a copy of all keys since we modify

            # A resource without an ID has been deleted.
            inventory_item = inventory[key]
            if 'id' in inventory_item and not inventory_item['id']:
                del inventory[key]

            # Remove AWS credentials
            # XXX(yoh) where do we get them from later?
            for secret_key in ('access_key_id', 'secret_access_key'):
                if secret_key in inventory_item:
                    del inventory_item[secret_key]

        with open(inventory_path, 'w') as fp:
            yaml.safe_dump(inventory, fp, default_flow_style=False)


class Resource(object):
    """
    Base class for creating and managing compute resources.
    """

    __metaclass__ = abc.ABCMeta

    def __repr__(self):
        return 'Resource({})'.format(self.name)

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

