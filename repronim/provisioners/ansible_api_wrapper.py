"""
    A wrapper class to provide simplifid access to the Ansible Python API 2.0.x
"""

import json
import os
import uuid
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase


class AnsibleApiWrapper:

    def __init__(self, target_host):
        self.target_host = target_host
        self.inventory_file = None
        self.tasks = []


    def add_task(self, task):
        self.tasks.append(task)


    def create_inventory_file(self):
        # Create a temporary inventory file.
        # inventory = """
        # [target_hosts]
        # 127.0.0.1

        # [target_hosts:vars]
        # customer_id=abc
        # customer_name=blah
        # customer_email=blah@blah.com
        # """

        inventory_filename = 'inventory-' + str(uuid.uuid1()) + '.txt'
        self.inventory_file = open(inventory_filename, 'w')
        # self.inventory_file.write(inventory)
        self.inventory_file.close()


    def destroy_inventory_file(self):
        os.remove(self.inventory_file.name)


    def run(self):

        self.create_inventory_file()

        Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check'])

        variable_manager = VariableManager()
        loader = DataLoader()
        options = Options(connection='local', module_path='/path/to/mymodules', forks=100, become=None, become_method=None, become_user=None, check=False)
        passwords = dict(vault_pass='secret')

        # Instantiate our ResultCallback for handling results as they come in
        results_callback = AnsibleResultCallback()

        # create inventory and pass to var manager
        inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=self.inventory_file.name)
        variable_manager.set_inventory(inventory)

        # create play with tasks
        play_source =  dict(
                name = "Ansible Play",
                hosts = self.target_host,
                gather_facts = 'no',
                tasks = self.tasks
            )
        play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

        # actually run it
        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=inventory,
                variable_manager=variable_manager,
                loader=loader,
                options=options,
                passwords=passwords,
                stdout_callback=results_callback,  # Use our custom callback instead of the ``default`` callback plugin
            )
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()
            self.destroy_inventory_file()


    def create_yaml_file(self):
        pass


class AnsibleResultCallback(CallbackBase):

    def v2_runner_on_ok(self, result, **kwargs):
        host = result._host
        print json.dumps({host.name: result._result}, indent=4)
