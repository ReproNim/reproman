# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to create an environment
"""

__docformat__ = 'restructuredtext'

from .base import Interface, backend_help, backend_set_config
import niceman.interface.base # Needed for test patching
# from ..formats import Provenance
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..support.exceptions import ResourceError
from ..resource import ResourceManager
from ..resource import Resource
from ..dochelpers import exc_str

from logging import getLogger
lgr = getLogger('niceman.api.create')


class Create(Interface):
    """Create a computation environment out from provided specification(s)

    Examples
    --------

      $ niceman create --spec recipe_for_failure.yml --name never_again

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
            args=("-n", "--name"),
            doc="""For which resource to create a new environment. To see
            available resources, run the command 'niceman ls'""",
            constraints=EnsureStr(),
        ),
        resource_type=Parameter(
            args=("-t", "--resource-type"),
            doc="""Resource type to create""",
            constraints=EnsureStr(),
        ),
        config = Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            constraints=EnsureStr(),
        ),
        resource_id=Parameter(
            args=("-id", "--resource-id",),
            doc="ID of environment container",
            constraints=EnsureStr(),
        ),
        clone=Parameter(
            args=("--clone",),
            doc="Name or ID of the resource to clone to another new resource",
            constraints=EnsureStr(),
        ),
        only_env=Parameter(
            args=("--only-env",),
            doc="only env spec",
            nargs="+",
            #action="store_true",
        ),
        existing=Parameter(
            args=("-e", "--existing"),
            choices=("fail", "redefine"),
            doc="Action to take if name is already known"
        ),
        backend=Parameter(
            args=("-b", "--backend"),
            nargs="+",
            doc=backend_help()
        ),
    )

    @staticmethod
    def __call__(name, resource_type, config, resource_id, clone, only_env,
                 backend, existing='fail '):

        # Load, while possible merging/augmenting sequentially
        # provenance = Provenance.factory(specs)
        #
        # TODO: need to be redone to be able to operate based on a spec
        #  we do want
        #     niceman create --resource_type docker_container --spec analysis.spec
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

        from niceman.ui import ui

        if not name and not resource_id:
            name = ui.question(
                "Enter a resource name",
                error_message="Missing resource name"
            )
        if not name:
            name = resource_id

        # if only_env:
        #     raise NotImplementedError

        # Get configuration and environment inventory
        if clone:
            config, inventory = ResourceManager.get_resource_info(config,
                clone, resource_id, resource_type)
            config['name'] = name
            del config['id']
            del config['status']
        else:
            config, inventory = ResourceManager.get_resource_info(config, name,
                resource_id, resource_type)

        # Create resource environment
        env_resource = ResourceManager.factory(config)

        # Set resource properties to any backend specific command line arguments.
        if backend:
            config = backend_set_config(backend, env_resource, config)

        env_resource.connect()
        resource_attrs = env_resource.create()

        # Save the updated configuration for this resource.
        config.update(resource_attrs)
        inventory[name] = config
        ResourceManager.set_inventory(inventory)

        lgr.info("Created the environment %s", name)

        # TODO: at the end install packages using install and created env
        # if not only_env:
        #     from repronim.api import install
        #     install(provenance, name, resource_id, config)