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
from .common_opts import resource_arg, resource_id_opt, resource_name_opt

from logging import getLogger
lgr = getLogger('niceman.api.login')


class Login(Interface):
    """Log into a computation environment

    Examples
    --------

      $ niceman login --resource=my-resource --config=niceman.cfg

    """

    _params_ = dict(
        resource=resource_arg,
        resource_id=resource_id_opt,
        resource_name=resource_name_opt,
        # XXX reenable when we support working with multiple instances at once
        # resource_type=resource_type_opt,
        # backend=Parameter(
        #     args=("-b", "--backend"),
        #     nargs="+",
        #     doc=backend_help()
        # ),

    )
    # XXX config option should be generic to niceman, so if someone
    #     wants to point to another niceman.cfg
    #
    # XXX Many commands will require specification of the resource
    #     which we are making "flexible" since could be one of the
    #     three ways to identify it
    #     - resource -- either a name or an id
    #     - resource_name, resource_id -- specific ones
    # eventually we might just want to have a helper decorator
    # @resource_method  which would handle the logic centrally and
    # just pass actual resource inside the __call__
    @staticmethod
    def __call__(resource=None, resource_name=None, resource_id=None):
        from niceman.ui import ui
        from niceman.resource import manager

        # Get a corresponding known resource
        env_resource = manager.get_resource(
            resource, name=resource_name, id_=resource_id)

        # TODO: reintroduce backend and also use of backend_set_config

        # Connect to resource environment
        env_resource.connect()
        with env_resource.get_session(pty=True):
            pass
        # env_resource.login()
