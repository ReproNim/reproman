# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to create an environment
"""

__docformat__ = 'restructuredtext'

from .base import Interface
import reproman.interface.base # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..support.exceptions import ResourceError
from ..resource import get_manager
from ..dochelpers import exc_str
from ..utils import parse_kv_list


from logging import getLogger
lgr = getLogger('reproman.api.create')


class Create(Interface):
    """Create a computation environment
    """

    _params_ = dict(
        # specs=Parameter(
        #     args=("-s", "--spec",),
        #     dest="specs",
        #     doc="file with specifications (in supported formats) of"
        #         " an environment where execution was originally executed",
        #     metavar='SPEC',
        #     # nargs="+",
        #     constraints=EnsureStr(),
        #     # TODO:  here we need to elaborate options for sub-parsers to
        #     # provide options, like --no-exec, etc  per each spec
        #     # ACTUALLY this type doesn't work for us since it is --spec SPEC SPEC... TODO
        # ),
        name=Parameter(
            args=("name",),
            metavar="NAME",
            doc="""Name of the resource to create""",
            constraints=EnsureStr(),
        ),
        resource_type=Parameter(
            args=("-t", "--resource-type"),
            doc="""Resource type to create""",
            constraints=EnsureStr(),
        ),
        # TODO: Implement --only-env and --existing.
        # only_env=Parameter(
        #     args=("--only-env",),
        #     doc="only env spec",
        #     nargs="+",
        #     #action="store_true",
        # ),
        # existing=Parameter(
        #     args=("-e", "--existing"),
        #     choices=("fail", "redefine"),
        #     doc="Action to take if name is already known"
        # ),
        backend_parameters=Parameter(
            metavar="PARAM",
            args=("-b", "--backend-parameters"),
            nargs="+",
            doc="""One or more backend parameters in the form KEY=VALUE. Use
            the command `reproman backend-parameters` to see the list of
            available backend parameters."""
        ),
    )

    @staticmethod
    def __call__(name, resource_type, backend_parameters):
        # Load, while possible merging/augmenting sequentially
        # provenance = Provenance.factory(specs)
        #
        # TODO: need to be redone to be able to operate based on a spec
        #  we do want
        #     reproman create --resource_type docker_container --spec analysis.spec
        #  which would choose appropriate base container etc
        #
        # if nothing in cmdline instructed on specific one to use:
        #   resource = Resource.factory(resource_type)
        #   resource_base = resource.guess_base(provenance.distributions)
        #
        # internally it might first just check if base OS could be deduced, so
        # we need helpers like
        #     guess_base_os_spec(distributions)
        # and if none is there, each resource, might provide/use defaults, e.g.
        # a default docker image if there is anaconda used and nothing about base
        # env.
        #
        # if not specs:
        #     specs = question("Enter a spec filename", default="spec.yml")

        from reproman.ui import ui

        if not resource_type:
            resource_type = ui.question(
                "Enter a resource type",
                default="docker-container"
            )
        # if only_env:
        #     raise NotImplementedError

        # TODO: Add ability to clone a resource.

        get_manager().create(name, resource_type,
                             parse_kv_list(backend_parameters))
        lgr.info("Created the environment %s", name)

        # TODO: at the end install packages using install and created env
        # if not only_env:
        #     from repronim.api import install
        #     install(provenance, name, resource_id, config)