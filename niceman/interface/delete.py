# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to delete an environment
"""

__docformat__ = 'restructuredtext'

import re

from .base import Interface, get_resource_info, set_resource_inventory, question
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..resource import Resource

from logging import getLogger
lgr = getLogger('niceman.api.delete')


class Delete(Interface):
    """Delete a computation environment

    Examples
    --------

      $ niceman delete --resource=my-resource --config=niceman.cfg

    """

    _params_ = dict(
        resource=Parameter(
            args=("-r", "--resource"),
            doc="""For which resource to create a new environment. To see
            available resource, run the command 'niceman ls'""",
            constraints=EnsureStr(),
        ),
        resource_type=Parameter(
            args=("-t", "--resource-type"),
            doc="""Resource type to create""",
            constraints=EnsureStr(),
        ),
        config=Parameter(
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
        skip_confirmation=Parameter(
            args=("--skip-confirmation",),
            action="store_true",
            doc="Delete resource without prompting user for confirmation",
        ),
    )

    @staticmethod
    def __call__(resource, resource_type, config, resource_id, skip_confirmation=False):

        if not resource and not resource_id:
            resource = question("Enter a resource name",
                                error_message="Missing resource name")

        # Get configuration and environment inventory
        config, inventory = get_resource_info(config, resource, resource_id, resource_type)

        # Delete resource environment
        env_resource = Resource.factory(config)
        env_resource.connect()

        if skip_confirmation:
            response = 'yes'
        else:
            response = question("Delete the resource '{}'? (ID: {})".format(
                env_resource.name, env_resource.id[:20]), default="No")

        if re.match('y|yes', response, re.IGNORECASE):

            env_resource.delete()

            # Save the updated configuration for this resource.
            if resource in inventory: del inventory[resource]
            set_resource_inventory(inventory)

            lgr.info("Deleted the environment %s", resource)