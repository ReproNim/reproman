# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

from niceman.distribution import Distribution


class DebianDistribution(Distribution):
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
        super(DebianDistribution, self).__init__(provenance)

    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        self._lgr.debug("Adding Debian update to environment command list.")
        environment.add_command(['apt-get', 'update'])
        environment.add_command(['apt-get', 'install', '-y', 'python-pip'])

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
            environment.add_command(
                # TODO: Pull env out of provenance for this command.
                ['apt-get', 'install', '-y', package['name']],
                # env={'DEBIAN_FRONTEND': 'noninteractive'}
            )