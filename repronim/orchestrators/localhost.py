"""
    A wrapper class to provide management to the localhost server.
"""

from repronim.orchestrator import Orchestrator
import subprocess

class LocalhostOrchestrator(Orchestrator):

    def __init__(self, provenance):
        super(LocalhostOrchestrator, self).__init__(provenance)

    def run(self):

        # Create the playbook.
        self.create_playbook_file()

        # Run Ansible playbook.
        print "\nRUNNING ANSIBLE PROVISIONER ****************************************************"
        command = [
            '/usr/bin/ansible-playbook',
            '-i',
            '"127.0.0.1,"',
            '-c',
            'local',
            'playbook.yml'
        ]
        output = subprocess.call(command)
        print output # Send the Ansible output to the screen.

    def create_playbook_file(self):
        # Ansible is particular about line spaces so we can't just do a yaml.dump() call, we
        # must write out the yaml file line by line.
        file = open('playbook.yml', 'w')
        file.write('---\n')
        file.write('- hosts: localhost\n')
        file.write('  become: yes\n')
        file.write('  tasks:\n')
        self.write_tasks_to_playbook(file)
        file.close()
