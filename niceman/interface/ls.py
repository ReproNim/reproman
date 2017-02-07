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

from .base import Interface
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
    )

    @staticmethod
    def __call__(names, config, verbose=False):

        resources = Resource.get_resources(config_path=config)

        template = '{:<30} {:<20} {:<20} {:<10} {:<20}'
        ui.message(template.format('RESOURCE NAME', 'TYPE', 'ID', 'STATUS', 'LOCATION'))
        ui.message(template.format('-----------', '----', '--', '------', '--------'))

        for name in resources:
            r = resources[name]
            if r.get_config('resource_id'):
                resource_id = r.get_config('resource_id')
            else:
                resource_id = '-'
            if r.get_config('resource_status'):
                resource_status = r.get_config('resource_status')
            else:
                resource_status = '-'
            if r.get_config('resource_backend'):
                resource_backend = r.get_config('resource_backend')
            else:
                resource_backend = '-'

            ui.message(template.format(
                name,
                r.get_config('resource_type'),
                resource_id,
                resource_status,
                resource_backend
            ))
