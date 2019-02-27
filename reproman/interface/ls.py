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

from collections import OrderedDict

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
        id_length = 19  # todo: make it possible to output them long
        template = '{:<20} {:<20} {:<%(id_length)s} {!s:<10}' % locals()
        ui.message(template.format('RESOURCE NAME', 'TYPE', 'ID', 'STATUS'))
        ui.message(template.format('-------------', '----', '--', '------'))

        results = OrderedDict()
        manager = get_manager()
        if not resrefs:
            resrefs = (manager.inventory[n]["id"] for n in sorted(manager)
                       if not n.startswith("_"))

        for resref in resrefs:
            try:
                resource = manager.get_resource(resref)
                name = resource.name
            except ResourceError as e:
                lgr.warning("Manager did not return a resource for %s: %s",
                            resref, exc_str(e))
                continue

            if refresh:
                try:
                    resource.connect()
                    if not resource.id:
                        resource.status = 'NOT FOUND'
                except Exception as e:
                    lgr.debug("%s resource query error: %s", name, exc_str(e))
                    resource.status = 'CONNECTION ERROR'

                manager.inventory[name].update({'status': resource.status})

            id_ = manager.inventory[name]['id']
            msgargs = (
                name,
                resource.type,
                id_[:id_length],
                resource.status,
            )
            ui.message(template.format(*msgargs))
            results[id_] = msgargs

        if refresh:
            manager.save_inventory()
        else:
            ui.message('Use --refresh option to view updated status.')
        return results
