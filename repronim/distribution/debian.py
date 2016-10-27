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


class DebianDistribution(Distribution):
    """
    Class to provide Debian-based shell commands.
    """

    def __init__(self, provenance):
        """
        Class constructor
        :param provenance: Instance of a Provenance sub-class.
        """
        super(DebianDistribution, self).__init__(provenance)

    def get_install_package_commands(self):
        """
        Returns a list of shell commands that install the packages specified
        by the given provenance.
        :return: Generator of shell commands. (Each command is a list of tokens.)
        """

        # Update apt-get before installing packages.
        command = ['apt-get', 'update']
        yield command

        # Return an install command for each package found in provenance.
        for package in self.provenance.get_packages():
            self.lgr.debug("Generating command for package: %s" % package['name'])
            command = [
                'apt-get',
                'install',
                '-y',
                package['name']
            ]
            yield command