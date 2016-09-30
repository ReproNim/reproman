# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to create an environment
"""

__docformat__ = 'restructuredtext'

from .base import Interface
from ..provenance_parser import ProvenanceParser
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from ..support.exceptions import InsufficientArgumentsError

from logging import getLogger
lgr = getLogger('repronim.api.create')


# STUBS for functionality to be moved into corresponding submodules

def get_known_backends():
    # TODO move
    # stub for nwo
    return 'docker', 'singularity', 'aws', 'native'


def create_env_from_spec(spec):
    # TODO
    return "The environment/image descriptor"

# Registry of already known/created environments.
# Definitely will not be just a dict but should support basic
# dict-like (associative array) interface
registry = {}


class Create(Interface):
    """Create a computation environment out from provided specification(s)

    Examples
    --------

      $ repronim create --spec recipe_for_failure.yml --name never_again

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
        backend=Parameter(
            choices=get_known_backends(),
            doc="""For which backend to create a new environment.""",
        ),

        # fast=Parameter(
        #     args=("-F", "--fast"),
        #     action="store_true",
        #     doc="only perform fast operations.  Would be overrident by --all",
        # ),
        # all=Parameter(
        #     args=("-a", "--all"),
        #     action="store_true",
        #     doc="list all entries, not e.g. only latest entries in case of S3",
        # ),
        # config_file=Parameter(
        #     doc="""path to config file which could help the 'ls'.  E.g. for s3://
        #     URLs could be some ~/.s3cfg file which would provide credentials""",
        #     constraints=EnsureStr() | EnsureNone()
        # ),
        # list_content=Parameter(
        #     choices=(None, 'first10', 'md5', 'full'),
        #     doc="""list also the content or only first 10 bytes (first10), or md5
        #     checksum of an entry.  Might require expensive transfer and dump
        #     binary output to your screen.  Do not enable unless you know what you
        #     are after""",
        #     default=None
        # ),
    )

    @staticmethod
    def __call__(specs, only_env=None, name=None, existing='fail',
                 backend=None):
        if not specs:
            raise InsufficientArgumentsError("Need at least a single --spec")

        if only_env:
            raise NotImplementedError

        if name in registry:
            # already exists
            raise ValueError("{} name is already known to the registry. ")

        # Load, while possible merging/augmenting sequentially
        lgr.info("Loading the specs %s", specs)
        spec = ProvenanceParser.chain_factory(specs)
        lgr.debug("SPEC: {}".format(spec))

        # Create
        env = create_env_from_spec(spec)

        if name is None:
            name = "some-fancy-unique-based-on-spec"

        lgr.info("Created the environment %s=%s", name, env)
        # Register within the registry
        registry[name] = env

        return env
