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
        inventory = manager.inventory

        id_length = 19  # todo: make it possible to output them long
        template = '{:<20} {:<20} {:<%(id_length)s} {:<10}' % locals()
        ui.message(template.format('RESOURCE NAME', 'TYPE', 'ID', 'STATUS'))
        ui.message(template.format('-------------', '----', '--', '------'))

        for name in sorted(inventory):
            if name.startswith('_'):
                continue

            # if refresh:
            inventory_resource = inventory[name]
            # XXX(yoh): why do we need a config here?
            config = dict(
                manager.config_manager.items(inventory_resource['type'].split('-')[0])
            )
            config.update(inventory_resource)
            # XXX Now we might have a dichotomy somewhat.  Key in the inventory
            #     is assumed to match a name as known to the resource.  But if not
            #     specified or mismatches -- what should we do?
            # #     For now let's just assume that every resource must have a name
            # #     and its name, if not specified, will be the key in the inventory
            if 'name' not in config:
                config['name'] = name
            try:
                env_resource = manager.factory(config)
            except Exception as e:
                lgr.error("Failed to create an instance from config: %s",
                          exc_str(e))
                continue
            try:
                if refresh:
                    env_resource.connect()
                # TODO: handle the actual refreshing in the inventory
                inventory_resource['id'] = env_resource.id
                inventory_resource['status'] = env_resource.status
                if not env_resource.id:
                    # continue  # A missing ID indicates a deleted resource.
                    inventory_resource['id'] = 'DELETED'
            except ResourceError as exc:
                ui.error("%s resource query error: %s" % (name, exc_str(exc)))
                for f in 'id', 'status':
                    inventory_resource[f] = inventory_resource.get(f, "?")
            msgargs = (
                name,
                inventory_resource['type'],
                inventory_resource['id'][:id_length],
                inventory_resource['status']
            )
            ui.message(template.format(*msgargs))
            lgr.debug('list result: {}, {}, {}, {}'.format(*msgargs))

        # if not refresh:
        #     ui.message('(Use --refresh option to view current status.)')
        #
        # if refresh:
        #     niceman.interface.base.set_resource_inventory(inventory)
