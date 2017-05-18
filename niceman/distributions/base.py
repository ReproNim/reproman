# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrators helping with management of target environments (remote or local)"""

from importlib import import_module
import abc

import logging
lgr = logging.getLogger('niceman.distributions')

class Distribution(object):
    """
    Base class for providing distribution-based shell commands.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, provenance):
        """
        Class constructor

        Parameters
        ----------
        provenance : object
            Provenance class instance
        """
        self._provenance = provenance

    @staticmethod
    def factory(distribution_type, provenance):
        """
        Factory method for creating the appropriate Orchestrator sub-class
        based on format type.

        Parameters
        ----------
        distribution_type : string
            Type of distribution subclass to create. Current options are:
            'conda', 'debian', 'neurodebian', 'pypi'
        provenance : object
            Provenance class instance.

        Returns
        -------
        distribution : object
            Instance of a Distribution sub-class
        """
        class_name = distribution_type.capitalize() + 'Distribution'
        module = import_module('niceman.distributions.' + distribution_type)
        return getattr(module, class_name)(provenance)

    @abc.abstractmethod
    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        return

    @abc.abstractmethod
    def install_packages(self, environment):
        """
        Install the packages associated to this distribution by the provenance
        into the environment.

        Parameters
        ----------
        environment : object
            Environment sub-class instance.
        """
        return
