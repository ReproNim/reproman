#!/bin/bash

set -eu

mkdir -p ~/.ssh

cat >>~/.ssh/config <<'EOF'

Host localhost
StrictHostKeyChecking no
IdentityFile /tmp/rman-test-ssh-id

Host reproman-test
StrictHostKeyChecking no
IdentityFile /tmp/rman-test-ssh-id
EOF

ssh-keygen -f /tmp/rman-test-ssh-id -N ""
cat /tmp/rman-test-ssh-id.pub >> ~/.ssh/authorized_keys
eval $(ssh-agent)
ssh-add /tmp/rman-test-ssh-id

cat ~/.ssh/config

echo "DEBUG: test connection to localhost ..."
ssh -v localhost exit
echo "DEBUG: test connection to reproman-test ..."
ssh -v reproman-test exit
