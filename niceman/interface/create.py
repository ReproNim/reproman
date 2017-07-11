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

import attr
from importlib import import_module
from .base import Interface
import niceman.interface.base # Needed for test patching
# from ..provenance import Provenance
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..support.exceptions import ResourceError
from ..resource import ResourceManager
from ..dochelpers import exc_str

from logging import getLogger
lgr = getLogger('niceman.api.create')


def backend_help(resource_type=None):
    types = ResourceManager._discover_types() if not resource_type else [resource_type]

    help_message = "One or more backend parameters in the form KEY=VALUE. Options are: "
    help_args = []

    for module_name in types:
        class_name = ''.join([token.capitalize() for token in module_name.split('_')])
        try:
            module = import_module('niceman.resource.{}'.format(module_name))
        except ImportError as exc:
            raise ResourceError(
                "Failed to import resource {}: {}.  Known ones are: {}".format(
                    module_name,
                    exc_str(exc),
                    ', '.join(ResourceManager._discover_types()))
            )
        cls = getattr(module, class_name)
        args = attr.fields(cls)
        for arg in args:
            if 'doc' in arg.metadata:
                help_args.append('"{}" ({})'.format(arg.name, arg.metadata['doc']))

    return help_message + ", ".join(help_args)


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
        resource=Parameter(
            args=("-r", "--resource"),
            # TODO:  is that a --name kind?  note that example mentions --name
            doc="""For which resource to create a new environment. To see
            available resource, run the command 'niceman ls'""",
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
    def __call__(resource, resource_type, config, resource_id, clone, only_env, backend, existing='fail '):

        # if not specs:
        #     specs = question("Enter a spec filename", default="spec.yml")

        # Load, while possible merging/augmenting sequentially
        # provenance = Provenance.factory(specs)

        from niceman.ui import ui

        if not resource:
            resource = ui.question(
                "Enter a resource name",
                error_message="Missing resource name"
            )

        # if only_env:
        #     raise NotImplementedError

        # Get configuration and environment inventory
        if clone:
            config, inventory = ResourceManager.get_resource_info(config, clone, resource_id, resource_type)
            config['name'] = resource
            del config['id']
            del config['status']
        else:
            config, inventory = ResourceManager.get_resource_info(config, resource, resource_id, resource_type)

        # Create resource environment
        env_resource = ResourceManager.factory(config)

        # Set resource properties to any backend specific command line arguments.
        for backend_arg in backend:
            key, value = backend_arg.split("=")
            if hasattr(env_resource, key):
                config[key] = value
                setattr(env_resource, key, value)
            else:
                raise NotImplementedError("Bad --backend paramenter '{}'".format(key))

        env_resource.connect()
        config_updates = env_resource.create()

        # Save the updated configuration for this resource.
        config.update(config_updates)
        inventory[resource] = config
        ResourceManager.set_inventory(inventory)

        lgr.info("Created the environment %s", resource)