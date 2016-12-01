# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Container sub-class to provide management of an AWS EC2 instance."""

import boto3

from repronim.container.base import Container
from repronim.support.sshconnector2 import SSHConnector2


class Ec2Container(Container):

    def __init__(self, resource, config={}):
        """
        Class constructor

        Parameters
        ----------
        resource : object
            Resource sub-class instance
        config : dictionary
            Configuration parameters for the container.
        """

        self._ec2_resource = None
        self._ec2_instance = None

        super(Ec2Container, self).__init__(resource, config)

        if not self.get_config('ami_id'):
            self.set_config('ami_id', 'ami-c8580bdf') # Ubuntu 14.04 LTS
        if not self.get_config('instance_type'):
            self.set_config('instance_type', 't2.micro')
        if not self.get_config('security_group'):
            self.set_config('security_group', 'default')

        # Initialize the connection to the AWS resource.
        self._ec2_resource = boto3.resource(
            'ec2',
            aws_access_key_id=self.get_config('aws_access_key_id'),
            aws_secret_access_key=self.get_config('aws_secret_access_key'),
            region_name=self.get_config('region_name')
        )

    def create(self):
        """
        Create an EC2 instance.
        """
        instances = self._ec2_resource.create_instances(
            ImageId=self.get_config('ami_id'),
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

    def execute_command(self, ssh, command, env=None):
        """
        Execute the given command in the container.

        Parameters
        ----------
        ssh : SSHConnector2 instance
            SSH connection object
        command : list
            Shell command string or list of command tokens to send to the
            container to execute.
        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call

        Returns
        -------
        list
            List of STDOUT lines from the container.
        """
        command_env = self.get_updated_env(env)

        if command_env:
            # TODO: might not work - not tested it
            command = ['export %s=%s;' % k for k in command_env.items()] + command

        stdout = ssh(" ".join(command))

        return stdout

    def execute_command_buffer(self):
        """
        Send all the commands in the command buffer to the container for
        execution.

        Returns
        -------
        list
            STDOUT lines from container
        """
        host = self._ec2_instance.public_ip_address
        key_filename = self.get_config('key_filename')

        with SSHConnector2(host, key_filename=key_filename) as ssh:
            for command in self._command_buffer:
                self._lgr.info("Running command '%s'", command['command'])
                stdout = self.execute_command(ssh, command['command'], command['env'])
                if stdout:
                    self._lgr.info("\n".join(stdout))