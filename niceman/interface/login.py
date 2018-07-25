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
from .common_opts import resource_id_opt
from .common_opts import resource_name_opt
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..resource import ResourceManager

from logging import getLogger
lgr = getLogger('niceman.api.login')


class Login(Interface):
    """Log into a computation environment

    Examples
    --------

      $ niceman login --name=my-resource

    """

    _params_ = dict(
        name=resource_name_opt,
        # XXX reenable when we support working with multiple instances at once
        # resource_type=Parameter(
        #     args=("-t", "--resource-type"),
        #     doc="""Resource type to work on""",
        #     constraints=EnsureStr(),
        # ),
        resource_id=resource_id_opt,
        backend=Parameter(
            args=("-b", "--backend"),
            nargs="+",
            doc=backend_help()
        ),
    )

    @staticmethod
    def __call__(name, backend, resource_id=None):
        from niceman.ui import ui
        if not name and not resource_id:
            name = ui.question(
                "Enter a resource name",
                error_message="Missing resource name"
            )

        # Get configuration and environment inventory
        # TODO: this one would ask for resource type whenever it is not found
        #       why should we???
        # TODO:  config too bad of a name here -- revert back to resource_info?
        config, inventory = ResourceManager.get_resource_info(name, resource_id)

        # Connect to resource environment
        env_resource = ResourceManager.factory(config)

        # Set resource properties to any backend specific command line arguments.
        if backend:
            config = backend_set_config(backend, env_resource, config)

        env_resource.connect()

        if not env_resource.id:
            raise ValueError("No resource found given the info %s" % str(config))

        with env_resource.get_session(pty=True):
            pass