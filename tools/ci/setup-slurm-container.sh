#!/bin/sh

set -eu

if ! test -f /tmp/rman-test-ssh-id
then
    echo "prep-travis-forssh.sh needs to executed before this script" >&2
    exit 1
fi

cat >>~/.ssh/config <<'EOF'

Host slurm
HostName localhost
Port 42241
User root
StrictHostKeyChecking no
IdentityFile /tmp/rman-test-ssh-id
EOF

docker run --name reproman-slurm-container \
       -dit -p 42241:22 -h ernie \
       repronim/reproman-slurm:latest

cat /tmp/rman-test-ssh-id.pub \
    | docker exec -i reproman-slurm-container \
             sh -c 'cat >>/root/.ssh/authorized_keys'

# Without the sleep below, the ssh call fails with
#
#   ssh_exchange_identification: read: Connection reset by peer
#
# A 10 second sleep is probably longer than we need, but a 3 second sleep did
# not seem to be enough:
# https://travis-ci.org/ReproNim/reproman/jobs/627568055#L584
sleep 10

echo "DEBUG: test connection to slurm container ..."
ssh -v slurm exit
