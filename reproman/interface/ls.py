# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
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

from .base import Interface
# import reproman.interface.base  # Needed for test patching
from ..support.param import Parameter
from ..resource import get_manager
from ..ui import ui
from ..support.exceptions import ResourceNotFoundError
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
    )

    @staticmethod
    def __call__(verbose=False, refresh=False):
        id_length = 19  # todo: make it possible to output them long
        template = '{:<20} {:<20} {:<%(id_length)s} {!s:<10}' % locals()
        ui.message(template.format('RESOURCE NAME', 'TYPE', 'ID', 'STATUS'))
        ui.message(template.format('-------------', '----', '--', '------'))

        manager = get_manager()
        for name in sorted(manager):
            if name.startswith('_'):
                continue

            try:
                resource = manager.get_resource(manager.inventory[name]['id'])
            except ResourceNotFoundError:
                lgr.warning("Manager did not return a resource for %r", name)
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

            msgargs = (
                name,
                resource.type,
                manager.inventory[name]['id'][:id_length],
                resource.status,
            )
            ui.message(template.format(*msgargs))
            lgr.debug('list result: {}, {}, {}, {}'.format(*msgargs))

        if refresh:
            manager.save_inventory()
        else:
            ui.message('Use --refresh option to view updated status.')
