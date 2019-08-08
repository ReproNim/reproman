#!/bin/sh

set -eu

echo "127.0.0.1  reproman-test" >> /etc/hosts
apt-get install openssh-client
