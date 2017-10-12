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

import os

from .base import Interface
import niceman.interface.base # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from  ..resource import ResourceManager
from ..ui import ui
from ..support.exceptions import ResourceError
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
        names=Parameter(
            doc="name of the specific environment(s) to be listed",
            metavar='NAME(s)',
            nargs="*",
            constraints=EnsureStr() | EnsureNone(),
        ),
        verbose=Parameter(
            args=("-v", "--verbose"),
            action="store_true",
            #constraints=EnsureBool() | EnsureNone(),
            doc="provide more verbose listing",
        ),
        config=Parameter(
            args=("--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            constraints=EnsureStr(),
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
    def __call__(names, config, verbose=False, refresh=False):

        # TODO?: we might want to embed get_resource_inventory()
        #       within ConfigManager (even though it would make it NICEMAN specific)
        #       This would allow to make more sensible error messages etc
        from niceman.resource import manager

        id_length = 19  # todo: make it possible to output them long
        template = '{:<20} {:<20} {:<%(id_length)s} {:<10}' % locals()
        ui.message(template.format('RESOURCE NAME', 'TYPE', 'ID', 'STATUS'))
        ui.message(template.format('-------------', '----', '--', '------'))

        for name in sorted(manager):
            resource = manager.get_resource(name=name)
            if name.startswith('_'):
                continue
            # XXX(yoh): why do we need a config here?  I guess to update some
            #   config settings which aren't recorded in the "inventory".  But
            #   all that should be done by the manager imho
            # config = dict(
            #     manager.config_manager.items(resource['type'].split('-')[0])
            # )
            # config.update(resource)
            # XXX Now we might have a dichotomy somewhat.  Key in the inventory
            #     is assumed to match a name as known to the resource.  But if not
            #     specified or mismatches -- what should we do?
            # #     For now let's just assume that every resource must have a name
            # #     and its name, if not specified, will be the key in the inventory
            # if not resource.name'name' not in config:
            #     config['name'] = ''
            # try:
            #     env_resource = manager.factory(config)
            # except Exception as e:
            #     lgr.error("Failed to create an instance from config: %s",
            #               exc_str(e))
            #     continue
            try:
                if refresh:
                    try:
                        resource.connect()
                    except Exception as exc:
                        lgr.warning("Cannot connect to the %s: %s", resource, exc_str(exc))
                if not resource.id:
                    # continue  # A missing ID indicates a deleted resource.
                    resource.id = 'DELETED'
                    # TODO: API to wipe those out
            except ResourceError as exc:
                ui.error("%s resource query error: %s" % (name, exc_str(exc)))
                for f in 'id', 'status':
                    if not getattr(resource, f):
                        setattr(resource, f, "?")
            msgargs = (
                name,
                resource.type,
                resource.id[:id_length],
                resource.status,
            )
            line = template.format(*msgargs)
            ui.message(line)
            lgr.debug('list result: %s', line)

        # if not refresh:
        #     ui.message('(Use --refresh option to view current status.)')
        #
        # if refresh:
        #     niceman.interface.base.set_resource_inventory(inventory)
        if refresh:
            lgr.debug("Storing manager's inventory upon refresh")
            # ATM it is not in effect, since inventory contains dicts, and
            # instances created "on the fly". TODO
            manager.set_inventory()