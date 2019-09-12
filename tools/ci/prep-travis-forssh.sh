#!/bin/bash

set -eu

mkdir -p ~/.ssh
echo -e "Host localhost\n\tStrictHostKeyChecking no\n\tIdentityFile /tmp/rman-test-ssh-id\n" >> ~/.ssh/config
echo -e "Host reproman-test\n\tStrictHostKeyChecking no\n\tIdentityFile /tmp/rman-test-ssh-id\n" >> ~/.ssh/config
ssh-keygen -f /tmp/rman-test-ssh-id -N ""
cat /tmp/rman-test-ssh-id.pub >> ~/.ssh/authorized_keys
eval $(ssh-agent)
ssh-add /tmp/rman-test-ssh-id

cat ~/.ssh/config

echo "DEBUG: test connection to localhost ..."
ssh -v localhost exit
echo "DEBUG: test connection to reproman-test ..."
ssh -v reproman-test exit
