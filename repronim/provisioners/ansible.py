"""
    A wrapper class to provide access to the Ansible platform.
"""

from repronim.provisioner import Provisioner
from jinja2 import Template
import subprocess

class AnsibleProvisioner(Provisioner):

    def __init__(self):
        self.playbook_file = 'playbook.yml'
        super(AnsibleProvisioner, self).__init__()

    def add_command(self, command, args):
        self.commands.append(dict(action=dict(module=command, args=args)))

    def run(self, target_host):

        # Create the playbook.
        self.create_playbook(target_host)

        # Run Ansible playbook.
        # /usr/bin/ansible-playbook -i "localhost," -c local playbook.yml
        print "\nRUNNING ANSIBLE PROVISIONER ****************************************************"
        command = [
            '/usr/bin/ansible-playbook',
            '-i',
            '"localhost,"',
            '-c',
            'local',
            self.playbook_file
        ]
        output = subprocess.call(command)
        print output # Send the Ansible output to the screen.

    def create_playbook(self, target_host):
        markup = """---
- hosts: {{ target_host }}
  become: yes

  tasks:
  {% for task in tasks %}- {{ task['action']['module'] }}:
      {% for key in task['action']['args'].keys() %}{{ key }}: '{{ task['action']['args'][key] }}'
      {% endfor %}
  {% endfor %}
  """
        t = Template(markup)
        file = open(self.playbook_file, 'w')
        file.write(t.render(target_host=target_host, tasks=self.commands))
        file.close()
