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

from .base import Interface
from ..provenance import Provenance
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from ..support.exceptions import InsufficientArgumentsError
from ..resource import ResourceConfig, Resource
import random

from logging import getLogger
lgr = getLogger('niceman.api.create')


# STUBS for functionality to be moved into corresponding submodules

def generate_environment_name():
    first_words = [
        'stamp',
        'languid',
        'annoyed',
        'kettle',
        'guard',
        'shape',
        'closed',
        'private',
        'barbarous',
        'preserve',
    ]
    second_words = [
        'pest',
        'purpose',
        'unequaled',
        'end',
        'scream',
        'uneven',
        'arithmetic',
        'zippy',
        'drop',
        'cheerful',
    ]

    name = '{0}_{1}'.format(random.choice(first_words), random.choice(second_words))
    return name


class Create(Interface):
    """Create a computation environment out from provided specification(s)

    Examples
    --------

      $ niceman create --spec recipe_for_failure.yml --name never_again

    """

    _params_ = dict(
        specs=Parameter(
            args=("--spec",),
            dest="specs",
            doc="file with specifications (in supported formats) of"
                " an environment where execution was originally executed",
            metavar='SPEC',
            nargs="+",
            constraints=EnsureStr(),
            # TODO:  here we need to elaborate options for sub-parsers to
            # provide options, like --no-exec, etc  per each spec
            # ACTUALLY this type doesn't work for us since it is --spec SPEC SPEC... TODO
        ),
        resource=Parameter(
            args=("-r", "--resource"),
            doc="""For which resource to create a new environment. To see
            available resource, run the command 'niceman ls'""",
            constraints=EnsureStr(),
        ),
        config = Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            constraints=EnsureStr(),
        ),
        image=Parameter(
            args=("-i", "--image",),
            doc="Image ID from which to create running instance",
            constraints=EnsureStr(),
        ),
        only_env=Parameter(
            args=("--only-env",),
            doc="only env spec",
            nargs="+",
            #action="store_true",
        ),
        name=Parameter(
            args=("-n", "--name"),
            metavar="NAME",
            constraints=EnsureStr() | EnsureNone(),
            doc="provide a name for the created environment",
        ),
        existing=Parameter(
            args=("-e", "--existing"),
            choices=("fail", "redefine"),
            doc="Action to take if name is already known"
        ),
    )

    @staticmethod
    def __call__(specs, resource, config, image, only_env,
                 name, existing='fail'):

        if not specs:
            raise InsufficientArgumentsError("Need at least a single --spec")
        print("SPEC: {}".format(specs[0]))

        # Load, while possible merging/augmenting sequentially
        # lgr.info("Loading the specs %s", specs)
        provenance = Provenance.factory(specs[0])
        lgr.debug("SPEC: {}".format(specs))

        if not resource:
            raise InsufficientArgumentsError("Need a --resource")
        Interface.validate_resource(resource, config, 'environment')
        print("RESOURCE: {}".format(resource))

        if only_env:
            raise NotImplementedError

        resource_config = ResourceConfig(resource, config_path=config)
        env_resource = Resource.factory(resource_config)

        if not name:
            name = generate_environment_name()
        else:
            pass
            # resource_client = env_resource.get_resource_client()
            # TODO: Get a listing of environments.
            # if name in resource_client.list_environments():
            #     raise ValueError(
            #         "{} environment is already known to the resource.", name)

        env_resource.create(name, image)

        lgr.info("Created the environment %s", name)