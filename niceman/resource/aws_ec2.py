# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of an AWS EC2 instance."""

import attr
import boto3
import re
from os import chmod
from os.path import join
from appdirs import AppDirs
from botocore.exceptions import ClientError

import logging
lgr = logging.getLogger('niceman.resource.aws_ec2')

from .base import Resource
from ..support.sshconnector2 import SSHConnector2
from ..ui import ui
from ..utils import assure_dir
from ..dochelpers import exc_str


@attr.s
class AwsEc2(Resource):

    # EC2 properties
    name = attr.ib()
    access_key_id = attr.ib()
    secret_access_key = attr.ib()
    id = attr.ib(default=None) # EC2 instance ID
    type = attr.ib(default='aws-ec2') # Resource type
    base_image_id = attr.ib(default='ami-c8580bdf')  # Ubuntu 14.04 LTS
    instance_type = attr.ib(default='t2.micro') # EC2 instance type
    security_group = attr.ib(default='default') # AWS security group
    region_name = attr.ib(default='us-east-1') # AWS region
    key_name = attr.ib(default=None) # Name of SSH key registered on AWS.
    key_filename = attr.ib(default=None) # SSH private key filename on local machine.
    status = attr.ib(default=None)

    # Management properties
    _ec2_resource = attr.ib(default=None)
    _ec2_instance = attr.ib(default=None)

    def connect(self):
        """
        Open a connection to the environment resource.
        """

        self._ec2_resource = boto3.resource(
            'ec2',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region_name
        )

        instances = []
        if self.id:
            instances.append(self._ec2_resource.Instance(self.id))
        elif self.name:
            instances = self._ec2_resource.instances.filter(
                Filters=[{
                        'Name': 'tag:Name',
                        'Values': [self.name]
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running']
                    }]
            )
            instances = list(instances)

        if len(instances) == 1:
            try:
                self._ec2_instance = instances[0]
                self.id = self._ec2_instance.instance_id
                self.status = self._ec2_instance.state['Name']
            except AttributeError:
                self.id = None
                self.status = None
        elif len(instances) > 1:
            raise Exception("Multiple container matches found")
        else:
            self.id = None
            self.status = None

    def create(self):
        """
        Create an EC2 instance.

        Returns
        -------
        dict : config and state parameters to capture in the inventory file
        """
        if self.id:
            raise Exception("Instance '{}' already exists in AWS subscription".format(
                self.id))

        if not self.key_name:
            self.create_key_pair()

        create_kwargs = dict(
            ImageId=self.base_image_id,
            InstanceType=self.instance_type,
            KeyName=self.key_name,
            MinCount=1,
            MaxCount=1,
            SecurityGroups=[self.security_group]
        )
        try:
            instances = self._ec2_resource.create_instances(**create_kwargs)
        except ClientError as exc:
            if re.search(
                "The key pair {} does not exist".format(self.key_name),
                str(exc)
            ):
                if not ui.yesno(
                    title="No key %s found in the "
                          "zone %s" % (self.key_name, self.region_name),
                    text="Would you like to generate a new key?"
                ):
                    raise
                self.create_key_pair(self.key_name)
                instances = self._ec2_resource.create_instances(**create_kwargs)
            else:
                raise  # re-raise

        # Give the instance a tag name.
        self._ec2_resource.create_tags(
            Resources=[instances[0].id],
            Tags=[{'Key': 'Name', 'Value': self.name}]
        )

        # Save the EC2 Instance object.
        self._ec2_instance = self._ec2_resource.Instance(instances[0].id)
        self.id = self._ec2_instance.instance_id

        lgr.info("Waiting for EC2 instance %s to start running...", self.id)
        self._ec2_instance.wait_until_running(
            Filters=[
                {
                    'Name': 'instance-id',
                    'Values': [self.id]
                },
            ]
        )
        lgr.info("EC2 instance %s to start running!", self.id)

        lgr.info("Waiting for EC2 instance %s to complete initialization...",
                 self.id)
        waiter = self._ec2_instance.meta.client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[self.id])
        lgr.info("EC2 instance %s initialized!", self.id)
        self.status = self._ec2_instance.state['Name']
        return {
            'id': self.id,
            'status': self.status,
            'key_name': self.key_name,
            'key_filename': self.key_filename
        }

    def delete(self):
        """
        Terminate this EC2 instance in the AWS subscription.
        """
        self._ec2_instance.terminate()

    def execute_command(self, ssh, command, env=None):
        """
        Execute the given command in the environment.

        Parameters
        ----------
        ssh : SSHConnector2 instance
            SSH connection object
        command : list
            Shell command string or list of command tokens to send to the
            environment to execute.
        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call
        """
        command_env = self.get_updated_env(env)

        # if command_env:
            # TODO: might not work - not tested it
            # command = ['export %s=%s;' % k for k in command_env.items()] + command

        # If a command fails, a CommandError exception will be thrown.
        for i, line in enumerate(ssh(" ".join(command))):
            lgr.debug("exec#%i: %s", i, line.rstrip())

    def execute_command_buffer(self):
        """
        Send all the commands in the command buffer to the environment for
        execution.
        """
        host = self._ec2_instance.public_ip_address

        with SSHConnector2(host, key_filename=self.key_filename) as ssh:
            for command in self._command_buffer:
                lgr.info("Running command '%s'", command['command'])
                self.execute_command(ssh, command['command'], command['env'])

    def create_key_pair(self, key_name=None):
        """
        Walk the user through creating an SSH key pair that is saved to
        the AWS platform.
        """

        if not key_name:
            prompt = """\
You did not specify an EC2 SSH key-pair name to use when creating your EC2
environment.
Please enter a unique name to create a new key-pair or press [enter] to exit"""
            key_name = ui.question(prompt)

        # Check to see if key_name already exists. 3 tries allowed.
        for i in range(3):
            # The user wants to exit.
            if not key_name:
                raise SystemExit("Empty keyname was provided, exiting")

            key_pair = self._ec2_resource.key_pairs.filter(KeyNames=[key_name])
            try:
                try:
                    len(list(key_pair))
                except ClientError as exc:
                    # Catch the exception raised when there is no matching
                    # key name at AWS.
                    if "does not exist" in str(exc):
                        break
                    # We have no clue what it is
                    raise
            except Exception as exc:
                lgr.error(
                    "Caught some unknown exception while checking key %s: %s",
                    key_pair,
                    exc_str(exc)
                )
                # reraising
                raise

            if i == 2:
                raise SystemExit('That key name exists already, exiting.')
            else:
                key_name = ui.question('That key name exists already, try again')

        # Create private key file.
        basedir = join(
            AppDirs('niceman', 'niceman.org').user_data_dir, 'ec2_keys')
        assure_dir(basedir)
        key_filename = join(basedir, key_name + '.pem')

        # Generate the key-pair and save to the private key file.
        key_pair = self._ec2_resource.create_key_pair(KeyName=key_name)
        with open(key_filename, 'w') as key_file:
            key_file.write(key_pair.key_material)
        chmod(key_filename, 0o400)
        lgr.info('Created private key file %s', key_filename)

        # Save the new info to the resource. This is later picked up and
        # saved to the resource inventory file.
        self.key_name = key_name
        self.key_filename = key_filename
