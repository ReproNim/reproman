# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrators helping with management of target environments (remote or local)"""

from importlib import import_module
import abc
import logging

class Distribution(object):
    """
    Base class for providing distribution-based shell commands.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, provenance):
        """
        Class constructor
        :param provenance: Instance of a Provenance sub-class.
        """
        self.provenance = provenance
        self.lgr = logging.getLogger('repronim.distribution')

    @staticmethod
    def factory(distribution_name, provenance):
        """
        Factory method for creating the appropriate Orchestrator sub-class based on format type.
        :param distribution_name: Keyword identifier for the target distribution. (e.g. debian, centos)
        :param provenance: Instance of Provenance sub-class.
        :return: Instance of the requested Distribution sub-class.
        """
        class_name = distribution_name.capitalize() + 'Distribution'
        module = import_module('repronim.distribution.' + distribution_name)
        return getattr(module, class_name)(provenance)

    def get_name(self):
        """
        Returns the environment operating system from provenance.
        :return: Operating system string
        """
        return self.provenance.get_os().lower()

    def get_version(self):
        """
        Returns the version of the environment operating system from provenance.
        :return: Operating system version string
        """
        return self.provenance.get_os_version()

    @abc.abstractmethod
    def get_install_package_commands(self):
        """
        Returns a list of shell commands that install the packages specified
        by the given provenance.
        :return: Generator of shell commands. (Each command is a list of tokens.)
        """
        return
