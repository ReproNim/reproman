# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to delete an environment
"""

__docformat__ = 'restructuredtext'

from .base import Interface
from .common_opts import resref_arg
from .common_opts import resref_type_opt
from ..dochelpers import exc_str
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..resource import get_manager

from logging import getLogger
lgr = getLogger('reproman.api.delete')


class Delete(Interface):
    """Delete a computation environment

    Examples
    --------

      $ reproman delete my-resource

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
        force=Parameter(
            args=("-f", "--force"),
            action="store_true",
            doc="""Remove a resource from the local inventory regardless of
            connection errors. Use with caution!""",
        ),
    )

    @staticmethod
    def __call__(resref, resref_type="auto", skip_confirmation=False,
                 force=False):

        from reproman.ui import ui

        manager = get_manager()
        resource = manager.get_resource(resref, resref_type)

        if skip_confirmation or force:
            delete_confirmed = True
        else:
            delete_confirmed = ui.yesno(
                "Delete the resource '{}'? (ID: {})".format(
                    resource.name, resource.id[:20]),
                default="no"
            )

        if delete_confirmed:
            try:
                resource.connect()
                manager.delete(resource)
            except Exception as exc:
                if force:
                    lgr.warning("Force deleting %s following failure: %s",
                                resource.name, exc_str(exc))
                    manager.delete(resource, inventory_only=True)
                else:
                    raise

            lgr.info("Deleted the environment %s", resource.name)
