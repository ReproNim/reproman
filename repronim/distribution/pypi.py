# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

from repronim.distribution import Distribution


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

    def initiate(self, container):
        """
        Perform any initialization commands needed in the container environment.

        Parameters
        ----------
        container : object
            The container sub-class object the hold the environment.
        """
        return

    def install_packages(self, container):
        """
        Install the packages associated to this distribution by the provenance
        into the container environment.

        Parameters
        ----------
        container : object
            Container sub-class instance.
        """
        for package in self.provenance['packages']:
            container.add_command(['pip', 'install', package['name']])
        return