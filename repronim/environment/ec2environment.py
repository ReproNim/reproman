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

from repronim.resource import Resource
from repronim.environment.base import Environment
from repronim.support.sshconnector2 import SSHConnector2


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
            aws_access_key_id=aws_client.get_config('aws_access_key_id'),
            aws_secret_access_key=aws_client.get_config('aws_secret_access_key'),
            region_name=self.get_config('region_name')
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
            self.set_config('name', name)
        if image_id:
            self.set_config('base_image_id', image_id)

        instances = self._ec2_resource.create_instances(
            ImageId=self.get_config('base_image_id'),
            InstanceType=self.get_config('instance_type'),
            KeyName=self.get_config('key_name'),
            MinCount=1,
            MaxCount=1,
            SecurityGroups=[self.get_config('security_group')],
        )

        # Give the instance a tag name.
        self._ec2_resource.create_tags(
            Resources=[instances[0].id],
            Tags=[{'Key': 'Name', 'Value': self.get_config('name')}]
        )

        # Save the EC2 Instance object.
        self._ec2_instance = self._ec2_resource.Instance(instances[0].id)

        self._lgr.info("Waiting for EC2 instance %s to start running...", self._ec2_instance.id)
        self._ec2_instance.wait_until_running(
            Filters=[
                {
                    'Name': 'instance-id',
                    'Values': [self._ec2_instance.id]
                },
            ]
        )
        self._lgr.info("EC2 instance %s to start running!", self._ec2_instance.id)

        self._lgr.info("Waiting for EC2 instance %s to complete initialization...", self._ec2_instance.id)
        waiter = self._ec2_instance.meta.client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[self._ec2_instance.id])
        self._lgr.info("EC2 instance %s initialized!")

    def connect(self, name=None):
        """
        Open a connection to the environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to connect to.
        """
        return


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

        if command_env:
            # TODO: might not work - not tested it
            command = ['export %s=%s;' % k for k in command_env.items()] + command

        for i, line in enumerate(ssh(" ".join(command))):
            if 'error' in line.lower():
                raise Exception("AWS error - %s" % line)
            self._lgr.debug("exec#%i: %s", i, line.rstrip())

    def execute_command_buffer(self):
        """
        Send all the commands in the command buffer to the environment for
        execution.
        """
        host = self._ec2_instance.public_ip_address
        key_filename = self.get_config('key_filename')

        with SSHConnector2(host, key_filename=key_filename) as ssh:
            for command in self._command_buffer:
                self._lgr.info("Running command '%s'", command['command'])
                self.execute_command(ssh, command['command'], command['env'])