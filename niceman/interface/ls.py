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

from .base import Interface, get_config_manager
import niceman.interface.base # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from  ..resource import Resource
from ..ui import ui

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
        # refresh=Parameter(
        #     args=("--refresh",),
        #     action="store_true",
        #     doc="Refresh the status of the resources listed",
        #     # metavar='CONFIG',
        #     # constraints=EnsureStr(),
        # ),
    )

    @staticmethod
    def __call__(names, config, verbose=False): #, refresh=False):

        # TODO?: we might want to embed get_resource_inventory()
        #       within ConfigManager (even though it would make it NICEMAN specific)
        #       This would allow to make more sensible error messages etc
        cm = get_config_manager(config)
        inventory_path = cm.getpath('general', 'inventory_file')
        inventory = niceman.interface.base.get_resource_inventory(inventory_path)

        template = '{:<20} {:<20} {:<20} {:<10}'
        ui.message(template.format('RESOURCE NAME', 'TYPE', 'ID', 'STATUS'))
        ui.message(template.format('-------------', '----', '--', '------'))

        for name in sorted(inventory):
            if name.startswith('_'):
                continue

            # if refresh:
            config = dict(cm.items(inventory[name]['type'].split('-')[0]))
            config.update(inventory[name])
            env_resource = Resource.factory(config)
            env_resource.connect()
            inventory[name]['id'] = env_resource.id
            inventory[name]['status'] = env_resource.status
            if not env_resource.id:
                continue # A missing ID indicates a deleted resource.

            ui.message(template.format(
                name,
                inventory[name]['type'],
                inventory[name]['id'][:19],
                inventory[name]['status']
            ))

            lgr.debug('list result: {}, {}, {}, {}'.format(name,
                inventory[name]['type'], inventory[name]['id'][:19],
                inventory[name]['status']))

        # if not refresh:
        #     ui.message('(Use --refresh option to view current status.)')
        #
        # if refresh:
        #     niceman.interface.base.set_resource_inventory(inventory)
