#!/bin/sh
echo "hello, world" > my-test-file.txt
sudo apt-get update
sudo apt-get install -y apache2 apache2-utils
