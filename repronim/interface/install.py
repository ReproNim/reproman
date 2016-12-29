# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to install packages
"""

__docformat__ = 'restructuredtext'

from .base import Interface
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from ..support.exceptions import InsufficientArgumentsError
from ..provenance import Provenance
from ..resource import Resource

from logging import getLogger
lgr = getLogger('repronim.api.install')


class Install(Interface):
    """Installs Debian packages out from provided specification(s)

    Examples
    --------

      $ repronim install --spec recipe_for_failure.yml --resource docker

    """

    _params_ = dict(
        spec=Parameter(
            args=("--spec",),
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
            args=("--resource",),
            doc="name of target resource to install spec on",
            metavar='RESOURCE',
            constraints=EnsureStr(),
        ),
        config=Parameter(
            args=("--config",),
            doc="path to repronim configuration file",
            metavar='CONFIG',
            constraints=EnsureStr(),
        ),
        name = Parameter(
            args=("--name", "-n"),
            metavar="NAME",
            constraints=EnsureStr() | EnsureNone(),
            doc="provide a name for the environment to connect",
        ),
    )

    @staticmethod
    def __call__(spec, resource, name, config=None):

        if not spec:
            raise InsufficientArgumentsError("Need at least a single --spec")
        print("SPEC: {}".format(spec))

        if not resource:
            raise InsufficientArgumentsError("Need at least a single --resource")
        print("RESOURCE: {}".format(resource))

        # TODO: Check to make sure resource_type is "environment"

        if not name:
            raise InsufficientArgumentsError("Need at least a single --name")
        print("NAME: {}".format(name))

        filename = spec[0]
        provenance = Provenance.factory(filename)

        env_resource = Resource.factory(resource, config_path=config)
        env_resource.connect(name)
        for distribution in provenance.get_distributions():
            distribution.initiate(env_resource)
            distribution.install_packages(env_resource)
        env_resource.execute_command_buffer()