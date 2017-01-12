# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of an AWS EC2 instance."""

import boto3
from os import chmod
from os.path import join
from appdirs import AppDirs
from botocore.exceptions import ClientError

from ..environment.base import Environment
from ..support.sshconnector2 import SSHConnector2
from ..ui import ui
from ..utils import assure_dir
from ..dochelpers import exc_str

import logging
lgr = logging.getLogger('repronim.environment.ec2')

class Ec2Environment(Environment):

    def __init__(self, config={}):
        """
        Class constructor

        Parameters
        ----------
        config : dictionary
            Configuration parameters for the environment.
        """
        if not 'base_image_id' in config:
            config['base_image_id'] = 'ami-c8580bdf' # Ubuntu 14.04 LTS
        if not 'instance_type' in config:
            config['instance_type'] = 't2.micro'
        if not 'security_group' in config:
            config['security_group'] = 'default'

        super(Ec2Environment, self).__init__(config)

        self._ec2_resource = None
        self._ec2_instance = None

        # Initialize the connection to the AWS resource.
        aws_client = self.get_resource_client()
        self._ec2_resource = boto3.resource(
            'ec2',
            aws_access_key_id=aws_client['aws_access_key_id'],
            aws_secret_access_key=aws_client['aws_secret_access_key'],
            region_name=self['region_name']
        )

    def create(self, name, image_id):
        """
        Create an EC2 instance.

        Parameters
        ----------
        name : string
            Name identifier of the environment to be created.
        image_id : string
            Identifier of the image to use when creating the environment.
        """
        if name:
            self['name'] = name
        if image_id:
            self['base_image_id'] = image_id
        if not 'key_name' in self:
            self.create_key_pair()

        instances = self._ec2_resource.create_instances(
            ImageId=self['base_image_id'],
            InstanceType=self['instance_type'],
            KeyName=self['key_name'],
            MinCount=1,
            MaxCount=1,
            SecurityGroups=[self['security_group']],
        )

        # Give the instance a tag name.
        self._ec2_resource.create_tags(
            Resources=[instances[0].id],
            Tags=[{'Key': 'Name', 'Value': self['name']}]
        )

        # Save the EC2 Instance object.
        self._ec2_instance = self._ec2_resource.Instance(instances[0].id)

        instance_id = self._ec2_instance.id
        self._lgr.info("Waiting for EC2 instance %s to start running...",
                       instance_id)
        self._ec2_instance.wait_until_running(
            Filters=[
                {
                    'Name': 'instance-id',
                    'Values': [instance_id]
                },
            ]
        )
        self._lgr.info("EC2 instance %s to start running!", instance_id)

        self._lgr.info("Waiting for EC2 instance %s to complete initialization...",
                       instance_id)
        waiter = self._ec2_instance.meta.client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[instance_id])
        self._lgr.info("EC2 instance %s initialized!", instance_id)

    def connect(self, name):
        """
        Open a connection to the environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to connect to.
        """
        instances = self._ec2_resource.instances.filter(
            Filters=[{
                'Name': 'tag:Name',
                'Values': [name]
            },
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }]
        )
        instances = list(instances)
        if len(instances) == 1:
            self._ec2_instance = instances[0]
        else:
            raise Exception("AWS error - No EC2 instance named {}".format(name))

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
            self._lgr.debug("exec#%i: %s", i, line.rstrip())

    def execute_command_buffer(self):
        """
        Send all the commands in the command buffer to the environment for
        execution.
        """
        host = self._ec2_instance.public_ip_address
        key_filename = self['key_filename']

        with SSHConnector2(host, key_filename=key_filename) as ssh:
            for command in self._command_buffer:
                self._lgr.info("Running command '%s'", command['command'])
                self.execute_command(ssh, command['command'], command['env'])

    def create_key_pair(self):
        """
        Walk the user through creating an SSH key pair that is saved to
        the AWS platform.
        """

        prompt = """
You did not specify an EC2 SSH key-pair name to use when creating your EC2 environment.
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
            AppDirs('repronim', 'repronim.org').user_data_dir, 'ec2_keys')
        assure_dir(basedir)
        key_filename = join(basedir, key_name + '.pem')

        # Generate the key-pair and save to the private key file.
        key_pair = self._ec2_resource.create_key_pair(KeyName=key_name)
        with open(key_filename, 'w') as key_file:
            key_file.write(key_pair.key_material)
        chmod(key_filename, 0o400)
        self._lgr.info('Created private key file %s', key_filename)

        # Save the new info to the resource.
        self['key_name'] = key_name
        self['key_filename'] = key_filename
        # TODO: Write new config info to the repronim.cfg file or a registry of some sort.
