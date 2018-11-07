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
from ..ui import ui
from ..utils import assure_dir, attrib
from ..dochelpers import exc_str
from ..support.exceptions import ResourceError
from .ssh import SSH

@attr.s
class AwsEc2(Resource):

    # Generic properties of any Resource
    name = attrib(default=attr.NOTHING)

    # Configurable options for each "instance"
    access_key_id = attrib(
        doc="AWS access key for remote access to your Amazon subscription.")
    secret_access_key = attrib(
        doc="AWS secret access key for remote access to your Amazon subscription")
    instance_type = attrib(default='t2.micro',
        doc="The type of Amazon EC2 instance to run. (e.g. t2.medium)")  # EC2 instance type
    security_group = attrib(default='default',
        doc="AWS security group to assign to the EC2 instance.")  # AWS security group
    region_name = attrib(default='us-east-1',
        doc="AWS availability zone to run the EC2 instance in. (e.g. us-east-1)")  # AWS region
    key_name = attrib(
        doc="AWS subscription name of SSH key-pair registered.")  # Name of SSH key registered on AWS.
    key_filename = attrib(
        doc="Path to SSH private key file matched with AWS key name parameter.") # SSH private key filename on local machine.
    image = attrib(default='ami-c8580bdf',
        doc="AWS image ID from which to create the running instance")  # Ubuntu 14.04 LTS
    user = attrib(default='ubuntu',
        doc="Login account to EC2 instance.")

    # Interesting one -- should we allow for it to be specified or should
    # it just become a property?  may be base class could
    id = attrib()  # EC2 instance ID

    # TODO: shouldn't be hardcoded???
    type = attrib(default='aws-ec2')  # Resource type

    # Current instance properties, to be set by us, not augmented by user
    status = attrib()

    # Resource and AWS instance objects
    _ec2_resource = attrib()
    _ec2_instance = attrib()

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
            raise ResourceError("Multiple container matches found")
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
            raise ResourceError("Instance '{}' already exists in AWS subscription".format(
                self.id))

        if not self.key_name:
            self.create_key_pair()

        create_kwargs = dict(
            ImageId=self.image,
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
            if re.search(
                "parameter groupId is invalid", str(exc)
            ):
                raise ValueError("Invalid AWS Security Group: '{}'".format(
                    self.security_group))
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

    def start(self):
        """
        Start this EC2 instance in the AWS subscription.
        """
        self._ec2_instance.start()

    def stop(self):
        """
        Stop this EC2 instance in the AWS subscription.
        """
        self._ec2_instance.stop()

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

    def get_session(self, pty=False, shared=None):
        """
        Log into remote EC2 environment and get the command line
        """
        if not self._ec2_instance:
            self.connect()

        ssh = SSH(
            self.name,
            host=self._ec2_instance.public_ip_address,
            user=self.user,
            key_filename=self.key_filename
        )

        return ssh.get_session(pty=pty, shared=shared)
