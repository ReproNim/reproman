# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to create an environment
"""

__docformat__ = 'restructuredtext'

from .base import Interface, get_resource_info
import niceman.interface.base # Needed for test patching
# from ..provenance import Provenance
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..resource import Resource

from logging import getLogger
lgr = getLogger('niceman.api.create')


class Create(Interface):
    """Create a computation environment out from provided specification(s)

    Examples
    --------

      $ niceman create --spec recipe_for_failure.yml --name never_again

    """

    _params_ = dict(
        # specs=Parameter(
        #     args=("-s", "--spec",),
        #     dest="specs",
        #     doc="file with specifications (in supported formats) of"
        #         " an environment where execution was originally executed",
        #     metavar='SPEC',
        #     # nargs="+",
        #     constraints=EnsureStr(),
        #     # TODO:  here we need to elaborate options for sub-parsers to
        #     # provide options, like --no-exec, etc  per each spec
        #     # ACTUALLY this type doesn't work for us since it is --spec SPEC SPEC... TODO
        # ),
        resource=Parameter(
            args=("-r", "--resource"),
            # TODO:  is that a --name kind?  note that example mentions --name
            doc="""For which resource to create a new environment. To see
            available resource, run the command 'niceman ls'""",
            constraints=EnsureStr(),
        ),
        resource_type=Parameter(
            args=("-t", "--resource-type"),
            doc="""Resource type to create""",
            constraints=EnsureStr(),
        ),
        config = Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            constraints=EnsureStr(),
        ),
        resource_id=Parameter(
            args=("-id", "--resource-id",),
            doc="ID of environment container",
            constraints=EnsureStr(),
        ),
        clone=Parameter(
            args=("--clone",),
            doc="Name or ID of the resource to clone to another new resource",
            constraints=EnsureStr(),
        ),
        image=Parameter(
            args=("-i", "--image",),
            doc="Base image ID from which to create the running instance",
            constraints=EnsureStr(),
        ),
        docker_engine_url=Parameter(
            args=("--docker-engine-url",),
            doc="URL where Docker engine is listening for connections",
            constraints=EnsureStr(),
        ),
        only_env=Parameter(
            args=("--only-env",),
            doc="only env spec",
            nargs="+",
            #action="store_true",
        ),
        aws_access_key_id=Parameter(
            args=("--aws-access-key-id",),
            doc="AWS access key for remote access to your Amazon subscription.",
            constraints=EnsureStr(),
        ),
        aws_secret_access_key=Parameter(
            args=("--aws-secret-access-key",),
            doc="AWS secret access key for remote access to your Amazon subscription",
            constraints=EnsureStr(),
        ),
        aws_instance_type=Parameter(
            args=("--aws-instance-type",),
            doc="The type of Amazon EC2 instance to run. (e.g. t2.medium)",
            constraints=EnsureStr(),
        ),
        aws_security_group=Parameter(
            args=("--aws-security-group",),
            doc="The Amazon security group to assign to the EC2 instance.",
            constraints=EnsureStr(),
        ),
        aws_region_name=Parameter(
            args=("--aws-region-name",),
            doc="The Amazon availability zone to run the EC2 instance in. (e.g. us-east-1)",
            constraints=EnsureStr(),
        ),
        aws_key_name=Parameter(
            args=("--aws-key-name",),
            doc="Name of SSH key-pair registered in your AWS subscription.",
            constraints=EnsureStr(),
        ),
        aws_key_filename=Parameter(
            args=("--aws-key-filename",),
            doc="Path to SSH private key file matched with AWS key name parameter.",
            constraints=EnsureStr(),
        ),
        existing=Parameter(
            args=("-e", "--existing"),
            choices=("fail", "redefine"),
            doc="Action to take if name is already known"
        ),
    )

    @staticmethod
    def __call__(resource, resource_type, config, resource_id, clone, image,
        docker_engine_url, only_env, aws_access_key_id, aws_secret_access_key,
        aws_instance_type, aws_security_group, aws_region_name, aws_key_name,
        aws_key_filename, existing='fail '):

        # if not specs:
        #     specs = question("Enter a spec filename", default="spec.yml")

        # Load, while possible merging/augmenting sequentially
        # provenance = Provenance.factory(specs)

        from niceman.ui import ui

        if not resource:
            resource = ui.question(
                "Enter a resource name",
                error_message="Missing resource name"
            )

        # if only_env:
        #     raise NotImplementedError

        # Get configuration and environment inventory
        if clone:
            config, inventory = get_resource_info(config, clone, resource_id, resource_type)
            config['name'] = resource
            del config['id']
            del config['status']
        else:
            config, inventory = get_resource_info(config, resource, resource_id, resource_type)

        # TODO: All resource-type-specific params handling should be done in some other
        # more scalable fashion
        # Overwrite file config settings with the optional ones from the command line.
        if image: config['base_image_id'] = image
        if docker_engine_url: config['engine_url'] = docker_engine_url
        if aws_access_key_id: config['access_key_id'] = aws_access_key_id
        if aws_secret_access_key: config['secret_access_key'] = aws_secret_access_key
        if aws_instance_type: config['instance_type'] = aws_instance_type
        if aws_security_group: config['security_group'] = aws_security_group
        if aws_region_name: config['region_name'] = aws_region_name
        if aws_key_name: config['key_name'] = aws_key_name
        if aws_key_filename: config['key_filename'] = aws_key_filename

        # Create resource environment
        env_resource = Resource.factory(config)
        env_resource.connect()
        config_updates = env_resource.create()

        # Save the updated configuration for this resource.
        config.update(config_updates)
        inventory[resource] = config
        niceman.interface.base.set_resource_inventory(inventory)

        lgr.info("Created the environment %s", resource)