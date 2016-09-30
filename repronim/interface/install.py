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
from ..orchestrator import Orchestrator

from logging import getLogger
lgr = getLogger('repronim.api.install')


class Install(Interface):
    """Installs Debian packages out from provided specification(s)

    Examples
    --------

      $ repronim install --spec recipe_for_failure.yml

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
        platform=Parameter(
            args=("--platform",),
            doc="platform to install environment [localhost|docker|aws|vagrant]",
            constraints=EnsureStr(),
        ),
        # only_env=Parameter(
        #     args=("--only-env",),
        #     doc="only env spec",
        #     nargs="+",
        #     #action="store_true",
        # ),
        # name=Parameter(
        #     args=("-n", "--name"),
        #     metavar="NAME",
        #     constraints=EnsureStr() | EnsureNone(),
        #     doc="provide a name for the created environment",
        # ),
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
    def __call__(spec, platform='localhost'):
        if not spec:
            raise InsufficientArgumentsError("Need at least a single --spec")
        print("SPEC: {}".format(spec))

        # Parse the provenance info in the spec to get the packages and their versions.
        filename = spec[0]
        provenance = Provenance.factory(filename, format='reprozip')

        # Install the packages on the target platform
        orchestrator = Orchestrator.factory(platform, provenance)
        orchestrator.install_packages()

