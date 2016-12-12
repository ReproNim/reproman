# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class to manage resources in which containers are created and run."""

from importlib import import_module
import abc
import logging

from ..config import ConfigManager
from ..support.exceptions import MissingConfigError


class Resource(object):
    """
    Base class for creating and managing compute resources.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, default_config, config):
        """
        Class constructor

        Parameters
        ----------
        default_config : dictionary
            Resource configuration settings from the repronim.cfg file.
        config : dictionary
            Configuration parameters for the resource that will override
            the default settings from the repronim.cfg file
        """
        self._default_config = default_config
        self._config = config
        self._lgr = logging.getLogger('repronim.resource')

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
        if config_path:
            cm = ConfigManager([config_path], False)
        else:
            cm = ConfigManager()
        if len(cm._sections) == 1:
            raise MissingConfigError("Cannot locate a repronim.cfg file.")

        default_config = dict(cm.items('resource ' + resource_id))
        if not default_config:
            raise MissingConfigError(
                "Cannot find resource %s in repronim.cfg file.", resource_id)
        if 'type' in default_config:
            resource_type = default_config['type']
        else:
            raise MissingConfigError(
                "Resource 'type' parameter missing for resource '%s'.", resource_id)

        # Translate the resource type into a class name.
        package_name = None
        if resource_type == 'localhost':
            package_name = 'localhost'
        if resource_type == 'aws':
            package_name = 'aws'
        if resource_type == 'docker':
            package_name = 'dockerengine'
        if resource_type == 'singularity':
            package_name = 'singularity'
        if not package_name:
            raise MissingConfigError("Resource package %s not found.", package_name)

        class_name = package_name.capitalize() + 'Resource'
        module = import_module('repronim.resource.' + package_name)
        instance = getattr(module, class_name)(default_config, config)
        return instance

    @abc.abstractmethod
    def get_container_list(self):
        """
        Query the resource and return a list of container information.

        Returns
        -------
        List of containers located at the resource.
        """
        return

    @abc.abstractmethod
    def get_image_list(self):
        """
        Query the resource and return a list of image information.

        Returns
        -------
        List of images located at the resource.
        """
        return

    def get_config(self, key):
        """
        Returns a configuration parameter indexed by the key.

        Parameters
        ----------
        key : string
            Identifier of configuration setting.

        Returns
        -------
        Value of configuration parameter indexed by the key.
        """
        if key in self._config:
            return self._config[key]

        if key in self._default_config:
            return self._default_config[key]

        raise MissingConfigError("Missing configuration parameter: '%s'" % key)

    def set_config(self, key, value):
        """
        Set a configuration parameter for the instance of the resource.

        Parameters
        ----------
        key : string
            Identifier of configuration setting.

        value : string
            Value of configuration setting.

        Returns
        -------

        """
        self._config[key] = value