# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
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

from logging import getLogger
lgr = getLogger('repronim.api.ls')


class Ls(Interface):
    """List known computation resources, images and environments

    Examples
    --------

      $ repronim ls
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
            doc="path to repronim configuration file",
            metavar='CONFIG',
            constraints=EnsureStr(),
        ),
    )

    @staticmethod
    def __call__(names, verbose=False, config=None):

        resources = Resource.get_resource_list(config_path=config)
        print '{: <30} {: <20}'.format('RESOURCE', 'TYPE')
        print '{: <30} {: <20}'.format('--------', '----')
        for resource in resources:
            print '{: <30} {: <20}'.format(resource['resource_id'], resource['resource_type'])
