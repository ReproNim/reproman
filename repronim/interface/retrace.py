# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Analyzes ReproZip YML configuration to gather detailed package information
"""

from .base import Interface
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..support.exceptions import InsufficientArgumentsError
from ..retrace import rpzutil
from logging import getLogger

__docformat__ = 'restructuredtext'

lgr = getLogger('repronim.api.retrace')


class Retrace(Interface):
    """Analyzes ReproZip files to gather detailed package information

    Examples
    --------

      $ repronim retrace --spec reprozip_run.yml > repronim_config.yml

    """

    _params_ = dict(
        spec=Parameter(
            args=("--spec",),
            doc="ReproZip YML file to be analyzed",
            metavar='SPEC',
            nargs="+",
            constraints=EnsureStr(),
        ),
    )

    @staticmethod
    def __call__(spec):

        if not spec:
            raise InsufficientArgumentsError("Need at least a single --spec")

        filename = spec[0]
        lgr.info("reading filename " + filename)
        rpz_env_config = rpzutil.read_reprozip_yaml(filename)
        # updated_config = identify_packages(rpz_env_config)
        # write_env_config(updated_config)
