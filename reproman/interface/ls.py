# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to list available environments
"""

__docformat__ = 'restructuredtext'

from functools import partial

from .base import Interface
# import reproman.interface.base  # Needed for test patching
from ..support.param import Parameter
from ..resource import get_manager
from ..ui import ui
from ..support.exceptions import ResourceError
from ..dochelpers import exc_str

from logging import getLogger
lgr = getLogger('reproman.api.ls')


class Ls(Interface):
    """List known computation resources, images and environments

    Examples
    --------

      $ reproman ls
    """

    _params_ = dict(
        verbose=Parameter(
            args=("-v", "--verbose"),
            action="store_true",
            doc="provide more verbose listing",
        ),
        refresh=Parameter(
            args=("-r", "--refresh",),
            action="store_true",
            doc="Refresh the status of the resources listed",
        ),
        resrefs=Parameter(
            args=("resrefs",),
            metavar="RESOURCE",
            nargs="*",
            doc="Restrict the output to this resource name or ID"
        ),
    )

    @staticmethod
    def __call__(resrefs=None, verbose=False, refresh=False):
        from pyout import Tabular

        manager = get_manager()
        if not resrefs:
            resrefs = (manager.inventory[n]["id"] for n in sorted(manager)
                       if not n.startswith("_"))

        table = Tabular(
            # Note: We're going with the name as the row key even though ID
            # would be the more natural choice because (1) inventory already
            # uses the name as the key, so we know it's unique and (2) sadly we
            # can't rely on the ID saying set after a .connect() calls (e.g.,
            # see docker_container.connect()).
            ["name", "type", "id", "status"],
            style={
                "default_": {"width": {"marker": "…", "truncate": "center"}},
                "header_": {"underline": True,
                            "transform": str.upper},
                "status": {"color":
                           {"re_lookup": [["^running$", "green"],
                                          ["^(stopped|exited)$", "red"],
                                          ["(ERROR|NOT FOUND)", "red"]]},
                           "bold":
                           {"re_lookup": [["(ERROR|NOT FOUND)", True]]}}})

        def get_status(res):
            if refresh:
                def fn():
                    try:
                        res.connect()
                    except Exception as e:
                        status = 'CONNECTION ERROR'
                    else:
                        status = res.status if res.id else 'NOT FOUND'
                    return status
                return "querying…", fn
            else:
                return res.status

        # Store a list of actions to do after the table is finalized so that we
        # don't interrupt the table's output.
        do_after = []
        # The refresh happens in an asynchronous call. Keep a list of resources
        # that we should ask pyout about once the table is finalized.
        resources_to_refresh = []
        with table:
            for resref in resrefs:
                try:
                    resource = manager.get_resource(resref)
                    name = resource.name
                except ResourceError as e:
                    do_after.append(
                        partial(lgr.warning,
                                "Manager did not return a resource for %s: %s",
                                resref,
                                exc_str(e)))
                    continue

                id_ = manager.inventory[name]['id']
                assert id_ == resource.id, "bug in resource logic"
                table([name,
                       resource.type,
                       id_,
                       get_status(resource)])
                resources_to_refresh.append(resource)

        if do_after or not refresh:
            # Distinguish between the table and added information.
            ui.message("\n")

        for fn in do_after:
            fn()

        if refresh:
            if resources_to_refresh:
                for res in resources_to_refresh:
                    name = res.name
                    status = table[(name,)]["status"]
                    manager.inventory[name].update({'status': status})
                manager.save_inventory()
        else:
            ui.message('Use --refresh option to view updated status.')
        return table
