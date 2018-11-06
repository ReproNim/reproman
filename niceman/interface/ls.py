# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to list available environments
"""

__docformat__ = 'restructuredtext'

from six.moves.configparser import NoSectionError

from .base import Interface
import niceman.interface.base # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from  ..resource import get_manager
from ..ui import ui
from ..support.exceptions import ResourceError
from ..support.exceptions import ResourceNotFoundError
from ..dochelpers import exc_str

from logging import getLogger
lgr = getLogger('niceman.api.ls')


class Ls(Interface):
    """List known computation resources, images and environments

    Examples
    --------

      $ niceman ls
    """

    _params_ = dict(
        verbose=Parameter(
            args=("-v", "--verbose"),
            action="store_true",
            #constraints=EnsureBool() | EnsureNone(),
            doc="provide more verbose listing",
        ),
        refresh=Parameter(
            args=("--refresh",),
            action="store_true",
            doc="Refresh the status of the resources listed",
            # metavar='CONFIG',
            # constraints=EnsureStr(),
        ),
    )

    @staticmethod
    def __call__(verbose=False, refresh=False):
        id_length = 19  # todo: make it possible to output them long
        template = '{:<20} {:<20} {:<%(id_length)s} {:<10}' % locals()
        ui.message(template.format('RESOURCE NAME', 'TYPE', 'ID', 'STATUS'))
        ui.message(template.format('-------------', '----', '--', '------'))

        manager = get_manager()
        for name in sorted(manager):
            if name.startswith('_'):
                continue

            # if refresh:
            try:
                resource = manager.get_resource(name, resref_type="name")
            except ResourceNotFoundError:
                lgr.warning("Manager did not return a resource for %r", name)
                continue

            try:
                if refresh:
                    resource.connect()
                if not resource.id:
                    # continue  # A missing ID indicates a deleted resource.
                    resource.id = 'DELETED'
                    resource.status = 'N/A'
                report_status = resource.status
            except Exception as exc:
                lgr.error("%s resource query error: %s", name, exc_str(exc))
                report_status = "N/A (QUERY-ERROR)"
                for f in 'id', 'status':
                    if not getattr(resource, f):
                        setattr(resource, f, "?")
            msgargs = (
                name,
                resource.type,
                resource.id[:id_length] if resource.id else '',
                report_status,
            )
            ui.message(template.format(*msgargs))
            lgr.debug('list result: {}, {}, {}, {}'.format(*msgargs))

        # if not refresh:
        #     ui.message('(Use --refresh option to view current status.)')
        #
        # if refresh:
        #     niceman.interface.base.set_resource_inventory(inventory)
