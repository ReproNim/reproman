"""
    Class to handle the management of target servers.
"""

from importlib import import_module
import abc

class Orchestrator(object):
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def factory(platform='aws'):
        class_name = platform.capitalize() + 'Orchestrator'
        module = import_module('repronim.orchestrators.' + platform)
        return getattr(module, class_name)()

    @abc.abstractmethod
    def start_server(self):
        ''' Kicks off a server to run an experiment on. '''
        return

    @abc.abstractmethod
    def get_target_host(self):
        ''' Returns the domain or IP of the target host. '''
        return
