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

from os.path import normpath
import sys
import time

from niceman.resource.session import get_local_session
from niceman.resource.session import Session
from .common_opts import resref_opt
from .common_opts import resref_type_opt
from .base import Interface
from ..support.constraints import EnsureNone
from ..support.constraints import EnsureStr
from ..support.exceptions import InsufficientArgumentsError
from ..support.param import Parameter
from ..utils import assure_list
from ..utils import to_unicode
from ..resource import get_manager

__docformat__ = 'restructuredtext'

from logging import getLogger
lgr = getLogger('niceman.api.retrace')


class Retrace(Interface):
    """Gather detailed package information from paths or a ReproZip trace file.

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
        resref=Parameter(
            args=("-r", "--resource",),
            dest="resref",
            metavar="RESOURCE",
            doc="""Name or ID of the resource to operate on. To see available
            resources, run 'niceman ls'.[PY: Note: As a special case, a session
            instance can be passed as the value for `resref`.  PY]""",
            constraints=EnsureStr() | EnsureNone()),
        resref_type=resref_type_opt,
    )

    # TODO: add a session/resource so we could trace within
    # arbitrary sessions
    @staticmethod
    def __call__(path=None, spec=None, output_file=None,
                 resref=None, resref_type="auto"):
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
        paths = map(to_unicode, paths)
        # The tracers assume normalized paths.
        paths = list(map(normpath, paths))

        if isinstance(resref, Session):
            # TODO: Special case for Python callers.  Is this something we want
            # to handle more generally at the interface level?
            session = resref
        elif resref:
            resource = get_manager().get_resource(resref, resref_type)
            session = resource.get_session()
        else:
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
        stream = open(output_file, "w") if output_file else sys.stdout
        NicemanProvenance.write(stream, spec)
        if stream is not sys.stdout:
            stream.close()


# TODO: session should be with a state.  Idea is that if we want
#  to trace while inheriting all custom PATHs which that run might have
#  had
def identify_distributions(files, session=None, tracer_classes=None):
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
    if tracer_classes is None:
        tracer_classes = get_tracer_classes()

    session = session or get_local_session()
    # TODO create list of appropriate for the `environment` OS tracers
    #      in case of no environment -- get current one
    # TODO: should operate in the session, might be given additional information
    #       not just files


    # .identify_ functions will have a side-effect of shrinking this list in-place
    # as they identify files beloning to them
    files_to_consider = set(files)

    distibutions = []
    files_processed = set()
    files_to_trace = files_to_consider

    niter = 0
    max_niter = 10
    while True:
        niter += 1
        nfiles_processed = len(files_processed)
        nfiles_to_trace = len(files_to_trace)
        lgr.info("Entering iteration #%d over Tracers", niter)
        if niter > max_niter:
            lgr.error(
                "We did %s iterations already, something is not right"
                % max_niter)
            break

        for Tracer in tracer_classes:
            lgr.debug("Tracing using %s", Tracer.__name__)
            # TODO: memoize across all loops
            # Identify directories from the files_to_consider
            dirs = set(filter(session.isdir, files_to_trace))

            # Pull out directories if the tracer can't handle them
            if Tracer.HANDLES_DIRS:
                files_to_trace = files_to_consider
                files_skipped = set()
            else:
                files_to_trace = files_to_consider - dirs
                files_skipped = files_to_consider - files_to_trace

            tracer = Tracer(session=session)
            begin = time.time()
            # yoh things the idea was that tracer might trace even without
            #     files, so we should not just 'continue' the loop if there is no
            #     files_to_trace
            if files_to_trace:
                remaining_files_to_trace = files_to_trace
                nenvs = 0
                for env, remaining_files_to_trace in tracer.identify_distributions(
                        files_to_trace):
                    distibutions.append(env)
                    nenvs += 1
                files_processed |= files_to_trace - remaining_files_to_trace
                files_to_trace = remaining_files_to_trace
                lgr.info("%s: %d envs with %d other files remaining",
                         Tracer.__name__,
                         nenvs,
                         len(files_to_trace))

            # Re-combine any files that were skipped
            files_to_consider = files_to_trace | files_skipped

            lgr.debug("Assigning files to packages by %s took %f seconds",
                      tracer, time.time() - begin)
        if len(files_to_trace) == 0 or (
            nfiles_processed == len(files_processed) and
            nfiles_to_trace == len(files_to_trace)):
            lgr.info("No more changes or files to track.  Exiting the loop")
            break

    return distibutions, files_to_consider


def get_tracer_classes():
    """A helper which returns a list of all available Tracers

    The order should not but does matter and ATM is magically provided
    """
    # TODO: automate discovery of available tracers
    from niceman.distributions.debian import DebTracer
    from niceman.distributions.redhat import RPMTracer
    from niceman.distributions.conda import CondaTracer
    from niceman.distributions.venv import VenvTracer
    from niceman.distributions.vcs import VCSTracer
    from niceman.distributions.docker import DockerTracer
    from niceman.distributions.singularity import SingularityTracer
    Tracers = [DebTracer, RPMTracer, CondaTracer, VenvTracer, VCSTracer,
        DockerTracer, SingularityTracer]
    return Tracers
