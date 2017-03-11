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

from .base import Interface, get_resource_info, question
import niceman.interface.base # Needed for test patching
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
            doc="""Name of the resource to consider. To see
            available resource, run the command 'niceman ls'""",
            constraints=EnsureStr(),
        ),
        # XXX reenable when we support working with multiple instances at once
        # resource_type=Parameter(
        #     args=("-t", "--resource-type"),
        #     doc="""Resource type to work on""",
        #     constraints=EnsureStr(),
        # ),
        resource_id=Parameter(
            args=("-id", "--resource-id",),
            doc="ID of the environment container",
            # constraints=EnsureStr(),
        ),
        skip_confirmation=Parameter(
            args=("--skip-confirmation",),
            action="store_true",
            doc="Delete resource without prompting user for confirmation",
        ),
        # TODO: should be moved into generic API
        config=Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            # constraints=EnsureStr(),
        ),
    )

    @staticmethod
    def __call__(resource, resource_id=None, skip_confirmation=False, config=None):

        if not resource and not resource_id:
            resource = question("Enter a resource name",
                                error_message="Missing resource name")

        # Get configuration and environment inventory
        resource_info, inventory = get_resource_info(config, resource, resource_id)

        # Delete resource environment
        env_resource = Resource.factory(resource_info)
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
            niceman.interface.base.set_resource_inventory(inventory)

            lgr.info("Deleted the environment %s", resource)