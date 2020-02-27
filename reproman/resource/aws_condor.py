# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of an AWS HTCondor cluster."""

import attr
import concurrent.futures
import logging
lgr = logging.getLogger('reproman.resource.aws_condor')

from .base import Resource
from ..resource import get_manager
from ..support.jobs.template import Template
from ..utils import attrib


@attr.s
class AwsCondor(Resource):

    # Generic properties of any Resource
    name = attrib(default=attr.NOTHING)

    # Configurable options
    size = attrib(
        default=2,
        doc="Number of EC2 instances in the HTCondor cluster.",
        converter=int
    )
    access_key_id = attrib(
        doc="AWS access key for remote access to your Amazon subscription.")
    secret_access_key = attrib(
        doc="AWS secret access key for remote access to your Amazon subscription.")
    instance_type = attrib(default="t2.medium",
        doc="The type of Amazon EC2 instance to run. (e.g. t2.medium)")  # EC2 instance type
    security_group = attrib(default="default",
        doc="AWS security group to assign to the EC2 instance.")  # AWS security group
    region_name = attrib(default="us-east-1",
        doc="AWS availability zone to run the EC2 instance in. (e.g. us-east-1)")  # AWS region
    key_name = attrib(
        doc="AWS subscription name of SSH key-pair registered.")  # Name of SSH key registered on AWS.
    key_filename = attrib(
        doc="Path to SSH private key file matched with AWS key name parameter.")  # SSH private key filename on local machine.
    image = attrib(default="ami-07ae3592c03add705",
        doc="AWS image ID from which to create the running instance.")  # NITRC-CE v0.51.0
    user = attrib(default='ubuntu',
        doc="Login account to EC2 instance.")

    id = attrib()
    nodes = attrib()  # Node 0 is the master node

    type = attrib(default="aws-condor")  # Resource type

    # Current instance properties, to be set by us, not augmented by user
    status = attrib()

    def connect(self):
        """
        Open a connection to the environment resources (all the nodes in the cluster).
        """
        resource_manager = get_manager()

        # Create an aws_ec2 instance definition for the master node plus each worker node.
        # Node 0 is the master node.
        if not self.nodes:
            self.nodes = []
            node_configs = []
            for i in range(self.size):
                node_configs.append({
                    "type": "aws-ec2",
                    "name": self.name + "_{}".format(i),
                    "access_key_id": self.access_key_id,
                    "secret_access_key": self.secret_access_key,
                    "instance_type": self.instance_type,
                    "security_group": self.security_group,
                    "region_name": self.region_name,
                    "key_name": self.key_name,
                    "key_filename": self.key_filename,
                    "image": self.image
                })
        else:
            node_configs = self.nodes
            self.nodes = []

        # Create a connection for each node in the cluster.
        for i in range(self.size):
            node = resource_manager.factory(node_configs[i])
            node.connect()
            self.nodes.append(node)

    def create(self):
        """
        Create a cluster of EC2 instances.

        Yields
        -------
        dict : config and state parameters to capture in the inventory file
        """
        inventory = {
            "type": "aws-condor",
            "name": self.name,
            "id": Resource._generate_id(),
            "access_key_id": self.access_key_id,
            "secret_access_key": self.secret_access_key,
            "instance_type": self.instance_type,
            "security_group": self.security_group,
            "region_name": self.region_name,
            "key_name": self.key_name,
            "key_filename": self.key_filename,
            "image": self.image,
            "nodes": [{
                "type": "aws-ec2",
                "name": "{}_{}".format(self.name, i)
            } for i in range(len(self.nodes))]
        }

        yield inventory

        def create_ec2(node):
            node_inventory = {}
            for resource_attrs in node.create():
                node_inventory.update(resource_attrs)
            return node_inventory

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for i, node_inventory in enumerate(executor.map(create_ec2, self.nodes)):
                inventory["nodes"][i].update(node_inventory)
                yield inventory

        lgr.info("Cluster %s is up and running!", self.name)

        for i, node in enumerate(self.nodes):
            if not node._ec2_instance.public_ip_address:
                node._ec2_instance = node._ec2_resource.Instance(node.id)
            condor_config = Template(
                central_manager_ip=self.nodes[0]._ec2_instance.private_ip_address,
                is_central_manager=(i == 0),
                worker_nodes=self.nodes[1:]
            ).render_cluster("condor_config.local.template")
            session = node.get_session()
            session.execute_command(["sudo", "chmod", "0777", "/etc/condor/config.d"])
            session.put_text(condor_config, "/etc/condor/config.d/00-nitrcce-cluster")
            session.execute_command(["sudo", "rm", "/etc/condor/config.d/00-minicondor"])
            session.execute_command(["sudo", "systemctl", "restart", "condor"])

        yield {
            'status': "Running"
        }

    def delete(self):
        """
        Terminate all the EC2 instances in the cluster.
        """
        for node in self.nodes:
            node.delete()

    def start(self):
        """
        Start all the EC2 instances in the cluster.
        """
        for node in self.nodes:
            node.start()

    def stop(self):
        """
        Stop all the EC2 instances in the cluster.
        """
        for node in self.nodes:
            node.stop()

    def get_session(self, pty=False, shared=None):
        """
        Log into remote HTCondor cluster (i.e. the manager node)
        """
        # Log into the central manager node
        return self.nodes[0].get_session(pty, shared)
