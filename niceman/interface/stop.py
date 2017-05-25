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

from .base import Interface, get_resource_info
import niceman.interface.base # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..resource import Resource

from logging import getLogger
lgr = getLogger('niceman.api.stop')


class Stop(Interface):
    """Stop a computation environment

    Examples
    --------

      $ niceman stop --resource=my-resource --config=niceman.cfg

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
        # TODO: should be moved into generic API
        config=Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            # constraints=EnsureStr(),
        ),
    )

    @staticmethod
    def __call__(resource, resource_id=None, config=None):
        from niceman.ui import ui
        if not resource and not resource_id:
            resource = ui.question(
                "Enter a resource name",
                error_message="Missing resource name"
            )

        # Get configuration and environment inventory
        # TODO: this one would ask for resource type whenever it is not found
        #       why should we???
        resource_info, inventory = get_resource_info(config, resource, resource_id)

        # Delete resource environment
        env_resource = Resource.factory(resource_info)
        env_resource.connect()

        if not env_resource.id:
            raise ValueError("No resource found given the info %s" % str(resource_info))

        env_resource.stop()

        lgr.info("Stopped the environment %s", resource)