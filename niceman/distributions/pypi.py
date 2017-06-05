# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

from niceman.distributions import Distribution

import logging
lgr = logging.getLogger('niceman.distributions.pypi')


class PypiDistribution(Distribution):
    """
    Class to provide Conda package management.
    """

    def __init__(self, provenance):
        """
        Class constructor

        Parameters
        ----------
        provenance : dictionary
            Provenance information for the distribution.
        """
        super(PypiDistribution, self).__init__(provenance)

    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        return

    def install_packages(self, environment):
        """
        Install the packages associated to this distribution by the provenance
        into the environment.

        Parameters
        ----------
        environment : object
            Environment sub-class instance.
        """
        for package in self._provenance['packages']:
            environment.add_command(['pip', 'install', package['name']])
        return