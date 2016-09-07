#!/bin/bash

# To run this file, the command is: "source setup.sh"
# Important! -- This script requires Ubuntu 14.04 to run properly.

PARENT_DIR="$(dirname "$(pwd)")"
export PYTHONPATH="${PYTHONPATH}:${PARENT_DIR}"

# # Install Ansible if needed.
# sudo apt-get install software-properties-common
# sudo apt-add-repository ppa:ansible/ansible
# sudo apt-get update
# sudo apt-get install ansible -y

# # Add packages needed for ansible-container.
# sudo apt-get install python-pip python-dev build-essential -y
# sudo pip install --upgrade pip
# sudo pip install --upgrade virtualenv
# wget https://bootstrap.pypa.io/ez_setup.py -O - | sudo python
# sudo apt-get update
# sudo apt-get install apt-transport-https ca-certificates
# sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
# sudo chmod 777 /etc/apt/sources.list.d
# sudo echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" > /etc/apt/sources.list.d/docker.list
# # sudo echo "deb https://apt.dockerproject.org/repo ubuntu-precise main" > /etc/apt/sources.list.d/docker.list
# sudo chmod 755 /etc/apt/sources.list.d
# sudo apt-get update
# sudo apt-get install linux-image-extra-$(uname -r) -y
# sudo apt-get install apparmor -y
# sudo apt-get update
# sudo apt-get install docker-engine -y
# sudo service docker start
# sudo pip install ansible-container

# # Build the necessary base Docker images for Docker environments.
# # Right now, we have one for Ubuntu/Precise.
# # NOTE: Be sure the user running this setup script is in the "docker" system group. See: /etc/group
# docker build -t repronim/ubuntu:precise -f dockerfiles/Dockerfile-ubuntu-precise dockerfiles
