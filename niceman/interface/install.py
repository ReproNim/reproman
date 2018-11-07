# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to install packages
"""

__docformat__ = 'restructuredtext'

from .base import Interface
from .common_opts import resref_arg
from .common_opts import resref_type_opt
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..formats import Provenance
from ..resource import get_manager

from logging import getLogger
lgr = getLogger('niceman.api.install')


class Install(Interface):
    """Install packages according to the provided specification(s)

    Examples
    --------

      $ niceman install docker recipe_for_failure.yml

    """

    _params_ = dict(
        resref=resref_arg,
        resref_type=resref_type_opt,
        spec=Parameter(
            args=("spec",),
            doc="file with specifications (in supported formats) of"
                " packages used in executed environment",
            metavar='SPEC',
            nargs="+",
            constraints=EnsureStr(),
            # TODO:  here we need to elaborate options for sub-parsers to
            # provide options, like --no-exec, etc  per each spec
            # ACTUALLY this type doesn't work for us since it is --spec SPEC SPEC... TODO
        ),
    )

    @staticmethod
    def __call__(resref, spec, resref_type="auto"):
        # Load, while possible merging/augmenting sequentially
        assert len(spec) == 1, "For now supporting having only a single spec"
        filename = spec[0]
        provenance = Provenance.factory(filename)

        # TODO
        #  - provenance might contain a 'base' which would instruct which
        #    resource to use

        env_resource = get_manager().get_resource(resref, resref_type)
        env_resource.connect()

        #  TODOs:
        #  - resource might be a backend, so we would need to do analysis
        #    to choose a base environment (e.g. docker image) first, given
        #    provenance details
        #  - might need to create a new session if by now we have only an
        #    "image" which cannot be used as a session right away
        #  - eventually we would need to implement an analysis to determine
        #    details of the provenance.distribution(s) before passing them
        #    for initiation/installation.  That would also "kick back" on the
        #    steps above making things "tricky" ;)

        # For now we deal with simple resources providing a session
        # and a complete, exhaustive and non conflicting with the specified
        # resource
        session = env_resource.get_session()
        environment_spec = provenance.get_environment()
        for distribution in environment_spec.distributions:
            # TODO: add option to skip initiation
            distribution.initiate(session)
            distribution.install_packages(session)
        #env_resource.execute_command_buffer()
        # ??? verify that everything was installed according to the specs
        #     so would need pretty much going through the spec and querying
        #     all those packages.  If something differs -- report
        # session.close()
        if environment_spec.files:
            lgr.warning("Got extra files listed %s", environment_spec.files)
