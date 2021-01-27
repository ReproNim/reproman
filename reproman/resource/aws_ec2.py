# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of an AWS EC2 instance."""

import attr
import boto3
import os
import os.path as op
import re
from os import chmod
from os.path import join
from time import sleep
from appdirs import AppDirs
from botocore.exceptions import ClientError

import logging
lgr = logging.getLogger('reproman.resource.aws_ec2')

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
    image = attrib(default='ami-0acbd99fe8c84efbb',
        doc="AWS image ID from which to create the running instance (Default: NITRC-CE)")  # NITRC-CE bionic for us-east-1
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

    @property
    def ec2_name(self):
        if self.name:
            return 'reproman-' + self.name
        return self.name

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
                        'Values': [self.ec2_name]
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running']
                    }]
            )
            instances = list(instances)

        if len(instances) > 1:
            lgr.warning("Multiple matches (%s) found for %s in %s region. We will use %s",
                        ', '.join(map(str, instances)), self.ec2_name, self.region_name, instances[0])

        if instances:
            try:
                self._ec2_instance = instances[0]
                if self.id is None:
                    lgr.debug("Assigning an instance ID %s", self._ec2_instance.instance_id)
                self.id = self._ec2_instance.instance_id
                self.status = self._ec2_instance.state['Name']
            except AttributeError:
                # TODO: WHY?
                self.id = None
                self.status = None
        else:
            self.id = None
            self.status = None

    def create(self):
        """
        Create an EC2 instance.
        
        There are 2 yields for the AWS create method. The first yield occurs
        immediately after the AWS service is sent the EC2 instance run command
        so that the instance details can immediately be saved to the
        inventory.yml file. The second yield occurs after the EC2 instance
        has fully spun up and the "running" status is saved to the
        inventory.yml file.

        Yields
        -------
        dict : config and state parameters to capture in the inventory file
        """
        if self.id:
            raise ResourceError("Instance '{}' already exists in AWS subscription".format(
                self.id))

        local_keys = self._get_local_keys()
        if not self.key_name:
            key_name = self.name  # self._ask_key_name()
            if key_name not in local_keys:
                self.create_key_pair(key_name)
            self.key_name = key_name

        if not self.key_filename:
            # So we have a key_name but not key_filename.
            # We can match
            if self.key_name in local_keys:
                lgr.debug("No key_filename, but found key %s among local keys", self.key_name)
                self.key_filename = local_keys[self.key_name]
            else:
                raise ValueError("No key_filename is specified, and no match found among locally available for key "
                                 "name %s" % self.key_name)

        # TODO: key_name might need to be changed if we are to store
        #  in the key_filename matching the key_name.  So here we need to RF
        #  to loop (to avoid one attempt in except on create_instances,
        #  and possibly ask for a new keyname
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
            Tags=[{'Key': 'Name', 'Value': self.ec2_name}]
        )

        # Save the EC2 Instance object.
        self._ec2_instance = self._ec2_resource.Instance(instances[0].id)
        self.id = self._ec2_instance.instance_id
        for t in range(3):
            try:
                self.status = self._ec2_instance.state['Name']
                break
            except ClientError as exc:
                if t == 2:
                    raise
                lgr.debug('Failed to get state (%s). Will try again', exc)
                sleep(3)

        # Send initial info back to be saved in inventory file.
        yield {
            'id': self.id,
            'status': self.status,
            'key_name': self.key_name,
            'key_filename': self.key_filename
        }

        lgr.info("Waiting for EC2 instance %s to start running...", self.id)
        self._ec2_instance.wait_until_running(
            Filters=[
                {
                    'Name': 'instance-id',
                    'Values': [self.id]
                },
            ]
        )
        lgr.info("EC2 instance %s is running!", self.id)

        lgr.info("Waiting for EC2 instance %s to complete initialization...",
                 self.id)
        waiter = self._ec2_instance.meta.client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[self.id])
        lgr.info("EC2 instance %s initialized!", self.id)
        self.status = self._ec2_instance.state['Name']
        yield {
            'status': self.status
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

    def create_key_pair(self, key_name):
        """
        Walk the user through creating an SSH key pair that is saved to
        the AWS platform.
        """
        # TODO: check above that if we raise below we do not create instance

        # Check to see if key_name already exists. 3 tries allowed.
        for i in range(3):
            # The user wants to exit.
            if not key_name:
                raise ValueError("Empty key name was provided, exiting")

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
        key_filename = self._get_matching_key_filename(key_name)

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

    @classmethod
    def _ask_key_name(cls):
        present_keys = cls._get_local_keys()
        prompt = ["You did not specify an EC2 SSH key-pair name to use when creating your EC2 environment."]
        if present_keys:
            prompt += ["%d keys were found locally: %s" % (len(present_keys), ' '.join(sorted(present_keys)))]
            prompt += ["You can enter one of the above key names to reuse an existing key"]
            prompt += ["or enter a new unique name to create a new key-pair."]
        else:
            prompt += ["Please enter a unique name to create a new key-pair."]
        prompt += ["Alternatively, press [enter] to exit"]
        key_name = ui.question((os.linesep + " ").join(prompt))
        return key_name

    @classmethod
    def _get_matching_key_filename(cls, key_name):
        """Helper to establish matching filename for the ssh key given the key name
        """
        return join(cls._get_key_directory(), key_name + '.pem')

    @classmethod
    def _get_local_keys(cls):
        """Return dict of key_name: key_filename for ssh key files found locally
        """
        d = cls._get_key_directory()
        return {f[:-4]: op.join(d, f)
                for f in os.listdir(d)
                if f.endswith('.pem') and op.isfile(op.join(d, f))}

    @classmethod
    def _get_key_directory(cls):
        """Return directory with ssh keys.

        It also ensures that the directory with keys exists locally
        """
        d = join(AppDirs('reproman', 'reproman.org').user_data_dir, 'ec2_keys')
        assure_dir(d)
        return d

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
