# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

from niceman.distributions.debian import DebianDistribution

import logging
lgr = logging.getLogger('niceman.distributions.neurodebian')

class NeurodebianDistribution(DebianDistribution):
    """
    Class to provide Debian-based shell commands.
    """

    def __init__(self, provenance):
        """
        Class constructor

        Parameters
        ----------
        provenance : dictionary
            Provenance information for the distribution.
        """
        super(NeurodebianDistribution, self).__init__(provenance)


    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """

        # TODO: Add code to setup NeuroDebian repository setup.

        super(NeurodebianDistribution, self).initiate(environment)