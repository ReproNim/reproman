"""
    Class to handle the management of target servers.
"""

from importlib import import_module
import abc

class Orchestrator(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, provenance):
        self.provenance = provenance
        self.tasks = [] # List of hashes with two keys: 'command' and 'args'. 'args' is a hash of command arguments.

    @staticmethod
    def factory(platform, provenance):
        class_name = platform.capitalize() + 'Orchestrator'
        module = import_module('repronim.orchestrators.' + platform)
        return getattr(module, class_name)(provenance)

    @abc.abstractmethod
    def create_playbook(self):
        ''' Create the YAML playbook file. '''
        return

    @abc.abstractmethod
    def run(self, target_server):
        ''' Execute all the tasks to provision the target server. '''
        return

    def add_task(self, command, args):
        self.tasks.append(dict(action=dict(module=command, args=args)))

    def write_tasks_to_playbook(self, file):
        for task in self.tasks:
            if (task['action']['module'] == 'apt' and task['action']['args'].has_key('name')):
                # This is a package install so we need to add install failure handling
                # for package versions that are no longer available. Currently, we fall back
                # on the most recent available version.
                file.write('  - name: Installing package %s\n    apt:' % task['action']['args']['name'])
                for key in task['action']['args'].keys():
                    file.write(" %s='%s'" % (key, task['action']['args'][key]))
                file.write('\n    register: result\n    ignore_errors: True')
                package_name = task['action']['args']['name'].split('=')[0]
                file.write('\n  - name: Installing most recent version of %s if necessary' % package_name)
                file.write('\n    apt:')
                for key in task['action']['args'].keys():
                    value = task['action']['args'][key]
                    if key == 'name':
                        value = value.split('=')[0]
                    file.write(" %s='%s'" % (key, value))
                file.write('\n    when: result|failed')
            else:
                # Write out a non-apt tasks to the playbook file.
                file.write('  - ' + task['action']['module'] + ':')
                for key in task['action']['args'].keys():
                    file.write(" %s='%s'" % (key, task['action']['args'][key]))
            file.write('\n')
