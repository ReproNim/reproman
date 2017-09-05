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

from .base import Interface, backend_help, backend_set_config
import niceman.interface.base # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..resource import ResourceManager

from logging import getLogger
lgr = getLogger('niceman.api.login')


class Login(Interface):
    """Log into a computation environment

    Examples
    --------

      $ niceman login --resource=my-resource --config=niceman.cfg

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
        backend=Parameter(
            args=("-b", "--backend"),
            nargs="+",
            doc=backend_help()
        ),
    )

    @staticmethod
    def __call__(resource=None, resource_name=None, resource_id=None, config=None):
        from niceman.ui import ui
        if not resource and not resource_id:
            resource = ui.question(
                "Enter a resource name",
                error_message="Missing resource name"
            )

        # Instantiate the resources manager
        manager = ResourceManager(config)
        # Get corresponding known resource
        env_resource = manager.get_resource(resource, name=resource, id_=resource_id)
        # Connect to resource environment
        env_resource.connect()
        env_resource.login()
