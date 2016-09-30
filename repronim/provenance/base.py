# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Parsers of provenance information"""

from importlib import import_module
import abc


class Provenance(object):
    """Base class to handle the collection and management of provenance information."""

    __metaclass__ = abc.ABCMeta

    @staticmethod
    def factory(source, format='reprozip'):
        """
        Factory method for creating the appropriate Provenance sub-class based on format type.
        :param source: File name or http endpoint containing provenance information.
        :param format: Format standard of provenance source.
        :return: Instance of the requested Provenance sub-class.
        """
        class_name = format.capitalize() + 'Provenance'
        module = import_module('repronim.provenance.' + format)
        return getattr(module, class_name)(source)

    @abc.abstractmethod
    def get_distribution(self):
        """
        :return: A dictionary containing 'OS' and 'version' keys
        """
        return

    @abc.abstractmethod
    def get_create_date(self):
        """
        :return: A dictionary containing a date string of when the workflow provenance was created
        """
        return

    @abc.abstractmethod
    def get_environment_vars(self):
        """
        :return: A list of tuples containing ('variable name', 'variable value')
        """
        return

    @abc.abstractmethod
    def get_packages(self):
        """
        :return: A list of dictionaries containing, for each package: 'name', 'version')
        """
        return
