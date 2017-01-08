# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class to manage compute resources."""

from importlib import import_module
import abc
import logging

from .config import ConfigManager
from .support.exceptions import MissingConfigError, MissingConfigFileError


class Resource(object):
    """
    Base class for creating and managing compute resources.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        """
        Class constructor

        Parameters
        ----------
        config : dictionary
            Configuration parameters for the resource.
        """
        self._config = config
        if not 'resource_id' in self._config:
            raise MissingConfigError("Missing 'resource_id' config parameter")

        self._lgr = logging.getLogger('repronim.resource')

    def __repr__(self):
        return 'Resource({})'.format(self._config['resource_id'])

    def __len__(self):
        return len(self._config)

    def __getitem__(self, item):
        return self._config[item]

    def __setitem__(self, key, value):
        self._config[key] = value

    def __contains__(self, item):
        return item in self._config

    @staticmethod
    def factory(resource_id, config = {}, config_path=None):
        """
        Factory method for creating the appropriate Container sub-class.

        Parameters
        ----------
        resource_id : string
            Identifier of a resource listed in the repronim.cfg file.
        config : dictionary
            Configuration parameters for the resource that will override
            the parameters in the repronim.cfg file
        config_path : string
            Path to repronim.cfg file if overriding the default file locations.
            Default file locations are described in repronim.config.py

        Returns
        -------
        Resource sub-class instance.
        """
        cm = Resource._get_config_manager(config_path)

        # Following statement throws exception, NoSectionError, if section
        # is missing from repronim.cfg file.
        default_config = dict(cm.items('resource ' + resource_id))

        # Override repronim.cfg settings with those passed in to the function.
        default_config.update(config)
        config = default_config

        # Store some useful info in the configuration.
        config['resource_id'] = resource_id
        config['config_path'] = config_path

        if 'resource_type' in config:
            class_type, class_base = config['resource_type'].split('-')
        else:
            raise MissingConfigError(
                "Resource 'resource_type' parameter missing for resource '%s'.", resource_id)

        class_name = class_type.capitalize() + class_base.capitalize()
        module = import_module('repronim.{1}.{0}{1}'.format(class_type, class_base))
        instance = getattr(module, class_name)(config)
        return instance

    @staticmethod
    def _get_config_manager(config_path=None):
        """
        Retrieve configuration manager object.

        Parameters
        ----------
        config_path : string
            Path to repronim.cfg file.

        Returns
        -------
        ConfigManager object
        """
        if config_path:
            cm = ConfigManager([config_path], False)
        else:
            cm = ConfigManager()
        if len(cm._sections) == 1:
            raise MissingConfigFileError("Unable to locate a repronim.cfg file.")

        return cm

    @staticmethod
    def get_resource_list(config_path=None):
        """
        Get the resources defined in the repronim.cfg file.

        Parameters
        ----------
        config_path : string
            Path to repronim.cfg file.

        Returns
        -------
        Dictionary containing the settings for all resources. The keys of
        the dictionary are the IDs of the resources.
        """
        cm = Resource._get_config_manager(config_path)

        resources = {}
        for name in cm._sections:
            if name.startswith('resource '):
                resource_id = name.split(' ')[-1]
                resources[resource_id] = cm._sections[name]
                resources[resource_id]['resource_id'] = resource_id
        return resources