# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Run a command/job on a remote resource.
"""

from argparse import REMAINDER
import collections
import logging
import yaml

from six.moves import shlex_quote

from niceman.interface.base import Interface
from niceman.interface.common_opts import resref_opt
from niceman.interface.common_opts import resref_type_opt
from niceman.support.jobs.orchestrators import ORCHESTRATORS
from niceman.support.jobs.submitters import SUBMITTERS
from niceman.resource import get_manager
from niceman.support.param import Parameter
from niceman.utils import parse_kv_list

lgr = logging.getLogger("niceman.api.run")

__docformat__ = "restructuredtext"


def _load_specs(files):
    ret = []
    for f in files:
        with open(f) as fh:
            ret.append(yaml.load(fh))
    return ret


def _combine_job_specs(specs):
    if not specs:
        return {}

    initial = specs[0]

    def update(d, u):
        """Like d.update(), but update mappings at all levels.

        Taken from https://stackoverflow.com/a/3233356
        """
        for k, v in u.items():
            if isinstance(v, collections.Mapping):
                d[k] = update(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    for spec in specs[1:]:
        update(initial, spec)
    return initial


class Run(Interface):
    """Run a command on the specified resource.
    """
    # TODO: Expand description.

    _params_ = dict(
        resref=resref_opt,
        resref_type=resref_type_opt,
        list_=Parameter(
            args=("--list",),
            dest="list_",
            action="store_true",
            doc="""Show available submitters and orchestrators instead of
            running a command."""),
        submitter=Parameter(
            args=("--submitter", "--sub"),
            metavar="NAME",
            doc="""Name of submitter. The submitter controls how the command
            should be submitted on the resource (e.g., with
            `condor_submit`)[CMD: . Use --list to see available submitters
            CMD]."""),
        orchestrator=Parameter(
            args=("--orchestrator", "--orc"),
            metavar="NAME",
            doc="""Name of orchestrator. The orchestrator performs pre- and
            post-command steps like setting up the directory for command
            execution and storing the results[CMD: . Use --list to see
            available orchestrators CMD]."""),
        # TODO: Make it possible to list available parameters for --js and -b.
        job_specs=Parameter(
            args=("--job-spec", "--js"),
            dest="job_specs",
            metavar="PATH",
            action="append",
            doc="""YAML files that define job parameters. Multiple paths can be
            given. If a parameter is defined in multiple specs, the value from
            the last path that defines it is used."""),
        job_parameters=Parameter(
            metavar="PARAM",
            dest="job_parameters",
            args=("-b", "--job-parameter"),
            # TODO: Use nargs=+ like create's --backend-parameters?  I'd rather
            # use 'append' there.
            action="append",
            doc="""A job parameter in the form KEY=VALUE. If the same parameter
            is defined via a job spec, the value given here takes
            precedence."""),
        inputs=Parameter(
            args=("-i", "--input"),
            dest="inputs",
            metavar="PATH",
            action="append",
            doc="""An input file to the command. How input files are used
            depends on the orchestrator, but, at the very least, the
            orchestrator should try to make these paths available on the
            resource."""),
        outputs=Parameter(
            args=("-o", "--output"),
            dest="outputs",
            metavar="PATH",
            action="append",
            doc="""An output file to the command. How output files are handled
            depends on the orchestrator."""),
        script=Parameter(
            args=("--script",),
            action="store_true",
            doc="""Print the run script rather than running the command."""),
        follow=Parameter(
            args=("--follow",),
            action="store_true",
            doc="""Continue to follow the submitted command instead of
            submitting it and detaching."""),
        command=Parameter(
            args=("command",),
            nargs=REMAINDER,
            metavar="COMMAND",
            doc="command for execution"),
    )

    @staticmethod
    def __call__(command=None, resref=None, resref_type="auto",
                 list_=False, submitter=None, orchestrator=None,
                 job_specs=None, job_parameters=None,
                 inputs=None, outputs=None,
                 script=False, follow=False):
        if list_:
            # TODO: The docstrings will need more massaging once they're
            # extended/improved.

            def fmt(d):
                return ["  {x.name}\n    {x.__doc__}".format(x=x)
                        for x in d.values()]

            print("\n".join(["Submitters"] + fmt(SUBMITTERS) +
                            [""] +
                            ["Orchestrators"] + fmt(ORCHESTRATORS)))
            return

        # TODO: inputs/outputs don't support globs like datalad run does.
        # We're not a datalad extension and don't even require datalad, so we
        # can't piggyback off of datalad's interface.  The best option I can
        # think of is the ugly inclusion of GlobbedPaths (and perhaps other
        # things) via the third-party branch.  This is just one of the places
        # where this lack of coupling and focus causes headache.  It's all very
        # ugly.

        # CLI things that can also be specified in spec.
        cli_spec = {
            k: v for k, v in
            {
                "submitter": submitter,
                "orchestrator": orchestrator,
                "inputs": inputs,
                "outputs": outputs,
            }.items()
            if v is not None
        }

        job_parameters = parse_kv_list(job_parameters)

        # Precedence: CLI option > CLI job parameter > spec file
        spec = _combine_job_specs(_load_specs(job_specs) +
                                  [job_parameters, cli_spec])

        # Treat "command" as a special case because it's a list and the
        # template expects a string.
        if not command and "command_str" in spec:
            pass
        elif command is None and "command" not in spec:
            raise ValueError("No command specified via CLI or job spec")
        else:
            command = command or spec["command"]
            # Unlike datalad run, we're only accepting a list form for now.
            command_str = " ".join(map(shlex_quote, command))
            spec["command"] = command
            spec["command_str"] = command_str

        resource = get_manager().get_resource(resref, resref_type)

        if orchestrator is None:
            # TODO: We could just set this as the default for the Parameter,
            # but it probably makes sense to have the default configurable per
            # resource.
            orchestrator = "datalad-pair"
        orchestrator_class = ORCHESTRATORS[orchestrator]
        orc = orchestrator_class(resource, submitter, spec)

        if script:
            # TODO: How to deal with submission template?
            print(orc.render_runscript())
        else:
            orc.prepare_remote(inputs)
            # TODO: Add support for templates via CLI.
            orc.submit()
            # TODO: Add support for querying/fetching without follow.
            if follow:
                orc.follow(outputs)
