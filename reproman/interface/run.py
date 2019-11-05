# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Run a command/job on a remote resource.
"""

from argparse import REMAINDER
import collections
import glob
import logging
import itertools
import textwrap
import yaml

from shlex import quote as shlex_quote

from reproman.interface.base import Interface
from reproman.interface.common_opts import resref_opt
from reproman.interface.common_opts import resref_type_opt
from reproman.support.jobs.local_registry import LocalRegistry
from reproman.support.jobs.orchestrators import Orchestrator
from reproman.support.jobs.orchestrators import ORCHESTRATORS
from reproman.support.jobs.submitters import SUBMITTERS
from reproman.resource import get_manager
from reproman.support.param import Parameter
from reproman.utils import parse_kv_list

lgr = logging.getLogger("reproman.api.run")

__docformat__ = "restructuredtext"


def _load_specs(files):
    ret = []
    for f in files:
        with open(f) as fh:
            ret.append(yaml.safe_load(fh))
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


def _parse_batch_params(params):
    """Transform batch parameter strings into lists of tuples.

    Parameters
    ----------
    params : list of str
        The string should have the form "key=val1,val2,val3".

    Returns
    -------
    A generator that, for each key, yields a list of key-value tuple pairs.
    """
    def maybe_glob(x):
        return glob.glob(x) if glob.has_magic(x) else [x]

    seen_keys = set()
    for param in params:
        if "=" not in param:
            raise ValueError(
                "param value should be formatted as 'key=value,...'")
        key, value_str = param.split("=", maxsplit=1)
        if key in seen_keys:
            raise ValueError("Key '{}' was given more than once".format(key))
        seen_keys.add(key)
        yield [(key, v)
               for v_unexpanded in value_str.split(",")
               for v in maybe_glob(v_unexpanded)]


def _combine_batch_params(params):
    """Transform batch parameter strings into records.

    Parameters
    ----------
    params : list of str
        The string should have the form "key=val1,val2,val3".

    Returns
    -------
    A generator that yields a record, computing the product from the values.

    >>> from pprint import pprint
    >>> params = ["k0=val1,val2,val3", "k1=val4,val5"]
    >>> pprint(list(_combine_batch_params(params)))
    [{'k0': 'val1', 'k1': 'val4'},
     {'k0': 'val1', 'k1': 'val5'},
     {'k0': 'val2', 'k1': 'val4'},
     {'k0': 'val2', 'k1': 'val5'},
     {'k0': 'val3', 'k1': 'val4'},
     {'k0': 'val3', 'k1': 'val5'}]
    """
    if not params:
        return
    # Note: If we want to support pairing the ith elements rather than taking
    # the product, we could add a parameter that signals to use zip() rather
    # than product(). If we do that, we'll also want to check that the values
    # for each key are the same length, probably in _parse_batch_params().
    for i in itertools.product(*_parse_batch_params(params)):
        yield dict(i)


def _resolve_batch_parameters(spec_file, params):
    """Determine batch parameters based on user input.

    Parameters
    ----------
    spec_file : str or None
        Name of YAML file the defines records of parameters.
    params : list of str or None
        The string should have the form "key=val1,val2,val3".

    Returns
    -------
    List of records or None if neither `spec_file` or `params` is specified.
    """
    if spec_file and params:
        raise ValueError(
            "Batch parameters cannot be provided with a batch spec")

    resolved = None
    if spec_file:
        with open(spec_file) as pf:
            resolved = yaml.safe_load(pf)
    elif params:
        resolved = list(_combine_batch_params(params))
    return resolved


JOB_PARAMETERS = collections.OrderedDict(
    [
        ("root_directory", Orchestrator.root_directory),
        ("working_directory", Orchestrator.working_directory),
        ("command_str, command",
         """Command to run (string and list form). A command will usually be
         set from the command line, but it can also be set in the job spec. If
         string and list forms are defined, the string form is used."""),
        ("submitter",
         """Name of submitter. The submitter controls how the command should be
         submitted on the resource (e.g., with `condor_submit`)."""),
        ("orchestrator",
         """Name of orchestrator. The orchestrator performs pre- and
         post-command steps like setting up the directory for command execution
         and storing the results."""),
        ("batch_spec",
         """YAML file that defines a series of records with parameters for
         commands. A command will be constructed for each record, with record
         values available in the command as well as the inputs and outputs as
         `{p[KEY]}`."""),
        ("batch_parameters",
         """Define batch parameters with 'KEY=val1,val2,...'. Different keys
         can be specified by giving multiple values, in which case the product
         of the values are taken. For example, 'subj=mei,satsuki' and 'day=1,2'
         would expand to four records, pairing each subj with each day. Values
         can be a glob pattern to match against the current working
         directory."""),
        ("inputs, outputs",
         """Input and output files (list) to the command."""),
        ("message",
         """Message to use when saving the run. The details depend on the orchestator,
         but in general this message will be used in the commit message."""),
        ("container",
         """Container to use for execution. This should match the name of a container
         registered with the datalad-container extension. This option is valid
         only for DataLad run orchestrators."""),
        # TODO: Add more information for the rest of these.
        ("memory, num_processes",
         """Supported by Condor and PBS submitters."""),
        ("num_nodes, walltime",
         """Supported by PBS submitter."""),
    ]
)


class Run(Interface):
    """Run a command on the specified resource.

    Two main options control how the job is executed: the orchestator and the
    submitter. The orchestrator that is selected controls details like how the
    data is made available on the resource and how the results are fetched. The
    submitter controls how the job is submitted on the resource (e.g., as a
    condor job). Use --list to see information on the available orchestrators
    and submitters.

    Unless --follow is specified, the job is started and detached. Use
    `reproman jobs` to list and fetch detached jobs.
    """
    _params_ = dict(
        resref=resref_opt,
        resref_type=resref_type_opt,
        list_=Parameter(
            args=("--list",),
            dest="list_",
            choices=('submitters', 'orchestrators', 'parameters', ''),
            doc="""Show available submitters, orchestrators, or job parameters.
            If an empty string is given, show all."""),
        submitter=Parameter(
            args=("--submitter", "--sub"),
            metavar="NAME",
            doc=(JOB_PARAMETERS["submitter"] +
                 "[CMD:  Use --list to see available submitters CMD]")),
        orchestrator=Parameter(
            args=("--orchestrator", "--orc"),
            metavar="NAME",
            doc=(JOB_PARAMETERS["orchestrator"] +
                 "[CMD:  Use --list to see available orchestrators CMD]")),
        batch_spec=Parameter(
            args=("--batch-spec", "--bs"),
            dest="batch_spec",
            metavar="PATH",
            doc=(JOB_PARAMETERS["batch_spec"] +
                 " See [CMD: --batch-parameter CMD][PY: `batch_parameters` PY]"
                 " for an alternative method for simple combinations.")),
        batch_parameters=Parameter(
            args=("--batch-parameter", "--bp"),
            dest="batch_parameters",
            action="append",
            metavar="PATH",
            doc=(JOB_PARAMETERS["batch_parameters"] +
                 " See [CMD: --batch-spec CMD][PY: `batch_spec` PY]"
                 " for specifying more complex records.")),
        job_specs=Parameter(
            args=("--job-spec", "--js"),
            dest="job_specs",
            metavar="PATH",
            action="append",
            doc="""YAML files that define job parameters. Multiple paths can be
            given. If a parameter is defined in multiple specs, the value from
            the last path that defines it is used[CMD: . Use --list to see
            available parameters for the built-in templates CMD]."""),
        job_parameters=Parameter(
            metavar="PARAM",
            dest="job_parameters",
            args=("--job-parameter", "--jp"),
            # TODO: Use nargs=+ like create's --backend-parameters?  I'd rather
            # use 'append' there.
            action="append",
            doc="""A job parameter in the form KEY=VALUE. If the same parameter
            is defined via a job spec, the value given here takes precedence.
            The values are available as fields in the templates used to
            generate both the run script and submission script[CMD: . Use
            --list to see available parameters for the built-in templates
            CMD]."""),
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
        message=Parameter(
            args=("-m", "--message"),
            metavar="MESSAGE",
            doc=JOB_PARAMETERS["message"]),
    )

    @staticmethod
    def __call__(command=None, message=None,
                 resref=None, resref_type="auto",
                 list_=None, submitter=None, orchestrator=None,
                 batch_spec=None, batch_parameters=None,
                 job_specs=None, job_parameters=None,
                 inputs=None, outputs=None,
                 follow=False):
        if list_ is not None:
            wrapper = textwrap.TextWrapper(
                initial_indent="    ",
                subsequent_indent="    ")

            def get_doc(x):
                doc = x if isinstance(x, str) else x.__doc__
                paragraphs = doc.replace("\n\n", "\0").split("\0")
                # Collapse whitespace.
                paragraphs = (" ".join(p.strip().split()) for p in paragraphs)
                return "\n\n".join(wrapper.fill(p) for p in paragraphs)

            def fmt(d):
                return ["  {}\n{}".format(k, get_doc(v))
                        for k, v in d.items()]

            # FIXME: We shouldn't bother calling fmt on items that aren't
            # selected by list=X.
            categories = [
                ("submitters", ["Submitters"] + fmt(SUBMITTERS)),
                ("orchestrators", ["Orchestrator"] + fmt(ORCHESTRATORS)),
                ("parameters", ["Job parameters"] + fmt(JOB_PARAMETERS)),
            ]
            items = []
            for c, lines in categories:
                if not list_ or c == list_:
                    items.extend(lines)
                    items.append("")
            print("\n".join(items))
            return

        # TODO: globbing for inputs/outputs and command string formatting is
        # only supported for DataLad-based orchestrators.

        # CLI things that can also be specified in spec.
        cli_spec = {
            k: v for k, v in
            {
                "message": message,
                "submitter": submitter,
                "orchestrator": orchestrator,
                "batch_spec": batch_spec,
                "batch_parameters": batch_parameters,
                "inputs": inputs,
                "outputs": outputs,
            }.items()
            if v is not None
        }

        job_parameters = parse_kv_list(job_parameters)

        # Precedence: CLI option > CLI job parameter > spec file
        spec = _combine_job_specs(_load_specs(job_specs or []) +
                                  [job_parameters, cli_spec])

        spec["_resolved_batch_parameters"] = _resolve_batch_parameters(
            spec.get("batch_spec"), spec.get("batch_parameters"))

        # Treat "command" as a special case because it's a list and the
        # template expects a string.
        if not command and "command_str" in spec:
            spec["_resolved_command_str"] = spec["command_str"]
        elif not command and "command" not in spec:
            raise ValueError("No command specified via CLI or job spec")
        else:
            command = command or spec["command"]
            # Unlike datalad run, we're only accepting a list form for now.
            spec["command"] = command
            spec["_resolved_command_str"] = " ".join(map(shlex_quote, command))

        if resref is None:
            if "resource_id" in spec:
                resref = spec["resource_id"]
                resref_type = "id"
            elif "resource_name" in spec:
                resref = spec["resource_name"]
                resref_type = "name"
            else:
                raise ValueError("No resource specified")
        resource = get_manager().get_resource(resref, resref_type)

        if "orchestrator" not in spec:
            # TODO: We could just set this as the default for the Parameter,
            # but it probably makes sense to have the default configurable per
            # resource.
            lgr.debug("No orchestrator specified; setting to 'plain'")
            spec["orchestrator"] = "plain"
        orchestrator_class = ORCHESTRATORS[spec["orchestrator"]]
        orc = orchestrator_class(resource, spec.get("submitter"), spec)

        orc.prepare_remote()
        # TODO: Add support for templates via CLI.
        orc.submit()

        lreg = LocalRegistry()
        lreg.register(orc.jobid, orc.as_dict())

        if follow:
            orc.follow()
            orc.fetch()
            lreg.unregister(orc.jobid)
