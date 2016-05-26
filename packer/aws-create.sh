#!/bin/sh
# Demo script to build an AMI on AWS.

packer build -var-file=aws-variables.json aws.json

