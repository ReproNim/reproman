# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Analyze ReproZip YML configuration to gather detailed package information
"""
import sys
from .base import Interface
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..support.constraints import EnsureNone
from ..support.exceptions import InsufficientArgumentsError
from ..retrace import rpzutil
from logging import getLogger

__docformat__ = 'restructuredtext'

lgr = getLogger('niceman.api.retrace')


class Retrace(Interface):
    """Analyze known (e.g. ReproZip) trace files or just paths to gather detailed package information

    Examples
    --------

      $ niceman retrace --spec reprozip_run.yml > niceman_config.yml

    """

    _params_ = dict(
        spec=Parameter(
            args=("--spec",),
            doc="ReproZip YML file to be analyzed",
            metavar='SPEC',
            # nargs="+",
            constraints=EnsureStr() | EnsureNone(),
        ),
        path=Parameter(
            args=("path",),
            metavar="PATH",
            doc="""path(s) to be traced.  If spec is provided, would trace them
            after tracing the spec""",
            nargs="*",
            constraints=EnsureStr() | EnsureNone()),
        output_file=Parameter(
            args=("-o", "--output-file",),
            doc="Output file.  If not specified - printed to stdout",
            metavar='output_file',
            constraints=EnsureStr() | EnsureNone(),
        ),
    )

    @staticmethod
    def __call__(path=None, spec=None, output_file=None):

        if not (spec or path):
            raise InsufficientArgumentsError("Need at least a single --spec or a file")

        if spec:
            lgr.info("reading spec file %s", spec)
            input_config = rpzutil.read_reprozip_yaml(spec)
        else:
            input_config = {}

        config = rpzutil.identify_packages(input_config, path)
        rpzutil.write_config(output_file or sys.stdout, config)
