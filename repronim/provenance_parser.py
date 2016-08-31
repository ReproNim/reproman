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


class ProvenanceParser(object):
    """Base (mostly abstract) class to handle the processing of provenance files.
    """

    __metaclass__ = abc.ABCMeta

    @staticmethod
    def factory(source, format='reprozip'):
        class_name = format.capitalize() + 'ProvenanceParser'
        module = import_module('repronim.provenance_parsers.' + format)
        return getattr(module, class_name)(source)

    @abc.abstractmethod
    def get_distribution(self):
        ''' Returns a hash containing 'OS' and 'version' keys '''
        return

    @abc.abstractmethod
    def get_create_date(self):
        ''' Returns a hash containing a date string of when the worflow provenance was created '''
        return

    @abc.abstractmethod
    def get_environment_vars(self):
        ''' Returns a list of tuples containing ('variable name', 'variable value') '''
        return

    @abc.abstractmethod
    def get_packages(self):
        ''' Returns a list of tuples containing ('package name', 'package version') '''
        return
