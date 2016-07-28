"""
    Class to handle the processing of provenance files and to
    manage the provenance information.
"""

from importlib import import_module
import abc

class ProvenanceParser(object):
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
    def get_environment_vars(self):
        ''' Returns a list of tuples containing ('variable name', 'variable value') '''
        return

    @abc.abstractmethod
    def get_packages(self):
        ''' Returns a list of tuples containing ('package name', 'package version') '''
        return
