"""
    A wrapper class to provide management of Docker containers.
"""

from repronim.orchestrator import Orchestrator
import os
import subprocess

class DockerOrchestrator(Orchestrator):

    def __init__(self, provenance):
        super(DockerOrchestrator, self).__init__(provenance)

    def run(self):

        # Create the ansible container context files.
        if not os.path.exists('ansible'):
            os.makedirs('ansible')
        self.create_container_file()
        self.create_playbook_file()
        self.create_requirements_file()

        # Run Ansible playbook.
        print("\nRUNNING ANSIBLE PROVISIONER ****************************************************")
        command = [
            '/usr/local/bin/ansible-container',
            'build'
        ]
        output = subprocess.call(command)
        print(output) # Send the Ansible output to the screen.

    def get_base_docker_image(self):
        distribution = self.provenance.get_distribution()
        if (distribution['OS'] == 'Ubuntu' and distribution['version'] == '12.04'):
            return 'repronim/ubuntu:precise'
        return ''

    def create_container_file(self):
        base_docker_image = self.get_base_docker_image()
        file = open('ansible/container.yml', 'w')
        file.write('version: "1"\n')
        file.write('services:\n')
        file.write('  default:\n')
        file.write('    image: %s\n' % (base_docker_image,))
        file.write('registries: {}')
        file.close()

    def create_playbook_file(self):
        # Ansible is particular about line spaces so we can't just do a yaml.dump() call, we
        # must write out the yaml file line by line.
        file = open('ansible/main.yml', 'w')
        file.write('---\n')
        file.write('- hosts: default\n')
        file.write('  tasks:\n')
        self.write_tasks_to_playbook(file)
        file.close()

    def create_requirements_file(self):
        file = open('ansible/requirements.yml', 'w')
        file.write('docker-py==1.8.0\n')
        file.close()
