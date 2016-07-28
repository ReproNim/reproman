"""
    Class to handle the the provisioning of servers based on the provenance data.
"""

from importlib import import_module
import abc

class Provisioner(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.commands = [] # List of hashes with two keys: 'command' and 'args'. 'args' is a hash of command arguments.

    @staticmethod
    def factory(platform='ansible'):
        class_name = platform.capitalize() + 'Provisioner'
        module = import_module('repronim.provisioners.' + platform)
        return getattr(module, class_name)()

    @abc.abstractmethod
    def add_command(self, command, args):
        ''' Give the provisioner a command to execute when it runs. '''
        return

    @abc.abstractmethod
    def run(self, target_server):
        ''' Execute all the commands to provision the target server. '''
        return
