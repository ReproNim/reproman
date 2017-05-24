# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""
Plugin support for provenance YAML files following NICEMAN spec.

"""
from __future__ import absolute_import

import collections
import datetime

import yaml

import niceman
from .. import utils
from ..dochelpers import exc_str
from ..distributions import Distribution
from .base import Provenance
from .utils import write_config_key

import logging
lgr = logging.getLogger('niceman.formats.niceman')


class NicemanspecProvenance(Provenance):
    """
    Parser for NICEMAN Spec (YAML specification)
    """

    def __init__(self, source=None, model=None):
        """
        Class constructor

        Parameters
        ----------
        source : string
            File path or URL
        """
        if source and model:
            raise ValueError("Provide either source or a model")
        self._model = model or self._load(source)

    @classmethod
    def _load(cls, source):
        """
        Load and store the raw spec file.

        Parameters
        ----------
        source : string
            File path or URL
        """
        with open(source, 'r') as stream:
            try:
                return yaml.load(stream)
            except yaml.YAMLError as exc:
                lgr.error("Failed to load %s: %s", source, exc_str(exc))
                raise  # TODO -- we might want a dedicated exception here

    def get_operating_system(self):
        """
        Retrieve the operating system information.

        Returns
        -------
        Dictionary containing name and version of the OS.
            os['name']
            os['version']
        """
        return self._model['distribution']

    def get_distributions(self):
        """
        Retrieve the information for all the distributions recorded in the
            file.

        Returns
        -------
        list
            List of Distribution sub-class objects.
        """
        dist_objects = []

        for dist_prov in self._model['distributions']:
            subclass = dist_prov['name'].strip('-0123456789')

            #Add relevant packages to the distribution provenance.
            dist_prov['packages'] = []
            for package in self._model['packages']:
                try:
                    # TODO: Improve handling of missing package lists.
                    if 'distributions' in package:
                        if 'distribution' in package:
                            raise ValueError(
                                "Only distribution or distributions must be provided")
                        distributions = package['distributions']
                    elif 'distribution' in package:
                        distributions = [{'name': package['distribution']}]
                    else:
                        raise ValueError(
                            "Provide a single or multiple distributions")

                    if isinstance(distributions, str):
                        # we were provided a single distribution so there were no list
                        distributions = [{'name': distributions}]
                    for package_dist in distributions:
                        if dist_prov['name'] == package_dist['name']:
                            dist_prov['packages'].append(package)
                except Exception as exc:
                    # Log error and keep going for now...
                    lgr.error("Failed to load package: %s, %s",
                              package['name'], exc_str(exc))

            dist_objects.append(Distribution.factory(subclass, dist_prov))

        return dist_objects


    # TODO: RF
    #   config must be gone and taken from self
    def write_config(self, output):
        """Writes an environment config to a stream
    
        Parameters
        ----------
        output
            Output Stream
    
        config : dict
            Environment configuration (input)
    
        """

        config = self._model
        # Allow yaml to handle OrderedDict
        # From http://stackoverflow.com/questions/31605131
        if collections.OrderedDict not in yaml.SafeDumper.yaml_representers:
            yaml.SafeDumper.add_representer(
                collections.OrderedDict,
                lambda self, data:
                self.represent_mapping('tag:yaml.org,2002:map', data.items()))

        envconfig = dict(config)  # Shallow copy for destruction
        utils.safe_write(
            output,
            ("# NICEMAN Environment Configuration File\n"
             "# This file was created by NICEMAN {0} on {1}\n").format(
                niceman.__version__, datetime.datetime.now()))

        c = "\n# Runs: Commands and related environment variables\n\n"
        write_config_key(output, envconfig, "runs", c)

        c = "\n# Package Origins \n\n"
        write_config_key(output, envconfig, "origins", c)

        c = "\n# Packages \n\n"
        write_config_key(output, envconfig, "packages", c)

        c = "\n# Non-Packaged Files \n\n"
        write_config_key(output, envconfig, "other_files", c)

        if envconfig:
            utils.safe_write(output, "\n# Other ReproZip keys (not used by NICEMAN) \n\n")
            utils.safe_write(output, yaml.safe_dump(envconfig,
                                                    encoding="utf-8",
                                                    allow_unicode=True))