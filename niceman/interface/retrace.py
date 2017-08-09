# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Analyze existing spec or session file system to gather more detailed information
"""

from __future__ import unicode_literals

import sys
import time

from niceman.resource.session import get_local_session
from .base import Interface
from ..support.constraints import EnsureNone
from ..support.constraints import EnsureStr
from ..support.exceptions import InsufficientArgumentsError
from ..support.param import Parameter
from ..utils import assure_list
from ..utils import to_unicode

__docformat__ = 'restructuredtext'

from logging import getLogger
lgr = getLogger('niceman.api.retrace')


class Retrace(Interface):
    """Analyze a known (e.g. ReproZip) trace files or just paths to gather detailed package information

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

    # TODO: add a session/resource so we could trace within
    # arbitrary sessions
    @staticmethod
    def __call__(path=None, spec=None, output_file=None):
        # heavy import -- should be delayed until actually used

        if not (spec or path):
            raise InsufficientArgumentsError(
                "Need at least a single --spec or a file"
            )

        paths = assure_list(path)
        if spec:
            lgr.info("reading spec file %s", spec)
            # TODO: generic loader to auto-detect formats etc
            from niceman.formats.reprozip import ReprozipProvenance
            spec = ReprozipProvenance(spec)
            paths += spec.get_files() or []

        # Convert paths to unicode
        paths = list(map(to_unicode, paths))

        session = get_local_session()

        # TODO: at the moment assumes just a single distribution etc.
        #       Generalize
        # TODO: RF so that only the above portion is reprozip specific.
        # If we are to reuse their layout largely -- the rest should stay as is
        (distributions, files) = identify_distributions(
            paths,
            session=session
        )
        from niceman.distributions.base import EnvironmentSpec
        spec = EnvironmentSpec(
            distributions=distributions,
        )
        if files:
            spec.files = sorted(files)

        # TODO: generic writer!
        from niceman.formats.niceman import NicemanProvenance
        NicemanProvenance.write(output_file or sys.stdout, spec)


# TODO: session should be with a state.  Idea is that if we want
#  to trace while inheriting all custom PATHs which that run might have
#  had
def identify_distributions(files, session=None):
    """Identify packages files belong to

    Parameters
    ----------
    files : iterable
      Files to consider

    Returns
    -------
    distributions : list of Distribution
    unknown_files : list of str
      Files which were not determined to belong to any specific distribution
    """
    # TODO: automate discovery of available tracers
    from niceman.distributions.debian import DebTracer
    from niceman.distributions.conda import CondaTracer
    from niceman.distributions.vcs import VCSTracer

    session = session or get_local_session()
    # TODO create list of appropriate for the `environment` OS tracers
    #      in case of no environment -- get current one
    # TODO: should operate in the session, might be given additional information
    #       not just files
    Tracers = [DebTracer, CondaTracer, VCSTracer]

    # .identify_ functions will have a side-effect of shrinking this list in-place
    # as they identify files beloning to them
    files_to_consider = files[:]

    distibutions = []
    for Tracer in Tracers:
        lgr.info("Tracing using %s", Tracer)
        if not files_to_consider:
            lgr.info("No files left to consider, not considering remaining tracers")
            break
        tracer = Tracer(session=session)
        begin = time.time()
        # might need to pass more into "identify_distributions" of the tracer
        for env, files_to_consider in tracer.identify_distributions(
                files_to_consider):
            distibutions.append(env)

        lgr.debug("Assigning files to packages by %s took %f seconds",
                  tracer, time.time() - begin)

    return distibutions, files_to_consider