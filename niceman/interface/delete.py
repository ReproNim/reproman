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
lgr = getLogger('niceman.api.delete')


class Delete(Interface):
    """Delete a computation environment

    Examples
    --------

      $ niceman delete my-resource

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
        skip_confirmation=Parameter(
            args=("--skip-confirmation",),
            action="store_true",
            doc="Delete resource without prompting user for confirmation",
        ),
    )

    @staticmethod
    def __call__(resref, resref_type="auto", skip_confirmation=False):
        from niceman.ui import ui

        manager = get_manager()
        resource = manager.get_resource(resref, resref_type)

        if skip_confirmation:
            response = True
        else:
            response = ui.yesno(
                "Delete the resource '{}'? (ID: {})".format(
                    resource.name, resource.id[:20]),
                default="no"
            )

        if response:
            resource.connect()
            manager.delete(resource)
            lgr.info("Deleted the environment %s", resource.name)
