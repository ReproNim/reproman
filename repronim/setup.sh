#!/bin/bash

# To run this file, the command is: "source setup.sh"

PARENT_DIR="$(dirname "$(pwd)")"
export PYTHONPATH="${PYTHONPATH}:${PARENT_DIR}"

# Install Ansible if needed.
if [ ! -f /usr/bin/ansible-playbook ]; then
	sudo apt-get install software-properties-common
	sudo apt-add-repository ppa:ansible/ansible
	sudo apt-get update
	sudo apt-get install ansible -y
else
	echo "Ansible is already installed!"
fi
