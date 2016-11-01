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
from ..support.constraints import EnsureStr
from ..support.exceptions import InsufficientArgumentsError
from ..provenance import Provenance
from ..container import Container
from .. import cfg

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
            doc="platform environment to install on",
            constraints=EnsureStr(),
            choices=['localhost', 'dockerengine'],
        ),
        # host=Parameter(
        #     args=("--host",),
        #     doc="host name or ip and port to install environment",
        #     constraints=EnsureStr(),
        # ),
        # image=Parameter(
        #     args=("--image",),
        #     doc="image name of environment",
        #     constraints=EnsureStr(),
        # ),
    )

    @staticmethod
    def __call__(spec, platform='dockerengine'):
        if not spec:
            raise InsufficientArgumentsError("Need at least a single --spec")
        print("SPEC: {}".format(spec))

        filename = spec[0]
        provenance = Provenance.factory(filename)

        with Container.factory(platform) as container:
            for distribution in provenance.get_distributions():
                distribution.initiate(container)
                distribution.install_packages(container)