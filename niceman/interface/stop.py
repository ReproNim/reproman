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

from .base import Interface
import niceman.interface.base # Needed for test patching
from .common_opts import resref_arg
from .common_opts import resref_type_opt
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..resource import get_manager

from logging import getLogger
lgr = getLogger('niceman.api.stop')


class Stop(Interface):
    """Stop a computation environment

    Examples
    --------

      $ niceman stop my-resource

    """

    _params_ = dict(
        resref=resref_arg,
        # XXX reenable when we support working with multiple instances at once
        # resource_type=Parameter(
        #     args=("-t", "--resource-type"),
        #     doc="""Resource type to work on""",
        #     constraints=EnsureStr(),
        # ),
        resref_type=resref_type_opt,
    )

    @staticmethod
    def __call__(resref, resref_type="auto"):
        manager = get_manager()
        resource = manager.get_resource(resref, resref_type)
        resource.connect()
        manager.stop(resource)
