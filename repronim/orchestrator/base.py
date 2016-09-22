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

class Orchestrator(object):
    """Base class for installing and managing environments on targeted servers."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, provenance):
        self.provenance = provenance
        self.lgr = logging.getLogger('repronim.orchestrator')

    @staticmethod
    def factory(platform, provenance):
        """
        Factory method for creating the appropriate Orchestrator sub-class based on format type.
        :param source: File name or http endpoint containing provenance information.
        :param format: Format standard of provenance source.
        :return: Instance of the requested provenance sub-class.
        """
        class_name = platform.capitalize() + 'Orchestrator'
        module = import_module('repronim.orchestrator.' + platform)
        return getattr(module, class_name)(provenance)

    @abc.abstractmethod
    def install_packages(self, target_server):
        """Install the packages listed in the provenance information."""
        return
