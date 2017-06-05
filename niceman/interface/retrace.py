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

import niceman.formats.niceman
from .base import Interface
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..support.constraints import EnsureNone
from ..support.exceptions import InsufficientArgumentsError
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

        # TODO: at the moment assumes just a single distribution etc.
        #       Generalize
        # TODO: RF so that only the above portion is reprozip specific.
        # If we are to reuse their layout largely -- the rest should stay as is
        from niceman.cmd import Runner
        (distributions, files) = identify_distributions(
            paths,
            session=Runner(env={'LC_ALL': 'C'})  # TODO: any/proper session
        )
        from niceman.distributions.base import EnvironmentSpec
        spec = EnvironmentSpec(
            distributions=distributions,
        )
        if files:
            spec['files'] = sorted(files)

        # TODO: generic writer!
        from niceman.formats.niceman import NicemanspecProvenance
        NicemanspecProvenance.write(output_file or sys.stdout, spec)


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
    from niceman.distributions.vcs import VCSTracer

    from niceman.cmd import Runner
    session = session or Runner(env={'LC_ALL': 'C'})
    # TODO create list of appropriate for the `environment` OS tracers
    #      in case of no environment -- get current one
    # TODO: should operate in the session, might be given additional information
    #       not just files
    Tracers = [DebTracer,]# VCSTracer]

    # .identify_ functions will have a side-effect of shrinking this list in-place
    # as they identify files beloning to them
    files_to_consider = files[:]

    distributions = []
    for Tracer in Tracers:
        tracer = Tracer(session=session)
        begin = time.time()
        # might need to pass more into "identify_distributions" of the tracer
        for dist in tracer.identify_distributions(files_to_consider):
            distributions.append(dist)

            # TODO RF: feels awkward to pass that dist now around... should
            # finally either merge Distribution with Tracer or may be create
            # DistributionInstance which would be the manipulator of a distribution
            # object specs.
            # Anyways retracing capabilities of asking for package detail
            # might also be used directly by the distribution, so may be
            # would make even more sense to join
            if len(dist.packages):
                raise NotImplementedError("Do not have capability yet to extend the list")

            packages, files_to_consider = tracer.identify_packages_from_files(files_to_consider)
            dist.packages.extend(packages)
            # TODO: dist.normalize()
            #   similar to DBs should take care about identifying/groupping etc
            #   of origins etc

            # packages_origins = tracer.identify_package_origins(packages_)
        lgr.debug("Assigning files to packages by %s took %f seconds",
                  tracer, time.time() - begin)

    return distributions, files_to_consider