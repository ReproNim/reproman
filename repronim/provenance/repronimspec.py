# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""
Plugin support for provenance YAML files following ReproNim spec.

See: https://vida-nyu.github.io/reprozip/
"""

import yaml

from ..dochelpers import exc_str
from .base import Provenance
from ..distribution import Distribution

import logging
lgr = logging.getLogger('repronim.provenance.repronimspec')


class RepronimspecProvenance(Provenance):
    """
    Parser for Repronim Spec provenance (YAML specification)
    """

    def __init__(self, source):
        """
        Class constructor

        Parameters
        ----------
        source : string
            Path or URL of provenance file.
        """
        self._yaml = None
        self._load(source)

    def _load(self, source):
        """
        Load and store the raw spec file.

        Parameters
        ----------
        source : string
            Filename or URL endpoint of the spec file.
        """
        with open(source, 'r') as stream:
            try:
                self._yaml = yaml.load(stream)
            except yaml.YAMLError as exc:
                lgr.error("Failed to load %s: %s", source, exc_str(exc))
                raise  # TODO -- we might want a dedicated exception here

    def get_distributions(self):
        """
        Retrieve the information for all the distributions recorded in the
            provenance file.

        Returns
        -------
        list
            List of Distribution sub-class objects.
        """
        dist_objects = []

        for dist_prov in self._yaml['distributions']:
            subclass = dist_prov['name'].strip('-0123456789')

            #Add relevant packages to the distribution provenance.
            dist_prov['packages'] = []
            for package in self._yaml['packages']:
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
                            "Provide a single distribution or even multiple distributions")

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
