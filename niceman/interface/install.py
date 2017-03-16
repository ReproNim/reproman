# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to install packages
"""

__docformat__ = 'restructuredtext'

from .base import Interface, get_resource_info
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..provenance import Provenance
from ..resource import Resource

from logging import getLogger
lgr = getLogger('niceman.api.install')


class Install(Interface):
    """Installs Debian packages out from provided specification(s)

    Examples
    --------

      $ niceman install --spec recipe_for_failure.yml --resource docker

    """

    _params_ = dict(
        spec=Parameter(
            args=("-s", "--spec",),
            doc="file with specifications (in supported formats) of"
                " packages used in executed environment",
            metavar='SPEC',
            nargs="+",
            constraints=EnsureStr(),
            # TODO:  here we need to elaborate options for sub-parsers to
            # provide options, like --no-exec, etc  per each spec
            # ACTUALLY this type doesn't work for us since it is --spec SPEC SPEC... TODO
        ),
        resource=Parameter(
            args=("-r", "--resource",),
            doc="name of target resource to install spec on",
            metavar='RESOURCE',
            constraints=EnsureStr(),
        ),
        resource_id=Parameter(
            args=("-id", "--resource-id",),
            doc="ID of environment to install resource on",
            constraints=EnsureStr(),
        ),
        config=Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            constraints=EnsureStr(),
        ),
    )

    @staticmethod
    def __call__(spec, resource, resource_id, config):

        from niceman.ui import ui
        if not spec:
            spec = [ui.question("Enter a spec filename", default="spec.yml")]

        if not resource and not resource_id:
            resource = ui.question("Enter a resource name",
                error_message="Missing resource name")

        # Load, while possible merging/augmenting sequentially
        filename = spec[0]
        provenance = Provenance.factory(filename)

        # Get configuration and environment inventory
        config, inventory = get_resource_info(config, resource, resource_id)

        env_resource = Resource.factory(config)
        env_resource.connect()
        for distribution in provenance.get_distributions():
            distribution.initiate(env_resource)
            distribution.install_packages(env_resource)
        env_resource.execute_command_buffer()
