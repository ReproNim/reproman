# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Operate on `reproman run` jobs.
"""

from functools import partial
import operator
import logging
import yaml

from reproman.dochelpers import exc_str
from reproman.interface.base import Interface
from reproman.support.external_versions import MissingExternalDependency
from reproman.support.jobs.local_registry import LocalRegistry
from reproman.support.jobs.orchestrators import ORCHESTRATORS
from reproman.resource import get_manager
from reproman.support.param import Parameter
from reproman.support.constraints import EnsureChoice
from reproman.support.exceptions import OrchestratorError
from reproman.support.exceptions import ResourceNotFoundError
from reproman.utils import chpwd

lgr = logging.getLogger("reproman.interface.jobs")

__docformat__ = "restructuredtext"


LREG = LocalRegistry()


def _load(job_file):
    with open(job_file) as jfh:
        return yaml.safe_load(jfh)


def match(query_id, jobids):
    """Match `query_id` against `job_ids`.

    Three types of matches are considered, in this order: full match or partial
    match. If there is a full match, partial matches are not considered.

    Parameters
    ----------
    query_id : str
        A candidate for a match or partial match with a known job ID.
    jobids : list of str
        Known job IDs.

    Returns
    -------
    Matched job ID (str) or None if there is no match.

    Raises
    ------
    ValueError if there are multiple hits for `query_id`.
    """
    query_fns = [operator.eq, operator.contains]
    for fn in query_fns:
        matches = [jobid for jobid in jobids if fn(jobid, query_id)]
        if len(matches) == 1:
            return matches[0]
        elif matches:
            # TODO: Use custom exception.
            raise ValueError("ID {} matches multiple jobs: {}"
                             .format(query_id, ", ".join(matches)))


def _resurrect_orc(job):
    resource = get_manager().get_resource(job["resource_id"], "id")
    try:
        # Create chpwd separately so that this try-except block doesn't cover
        # the context manager suite below.
        cd = chpwd(job["local_directory"])
    except FileNotFoundError:
        raise OrchestratorError(
            "local directory for job {} no longer exists: {}"
            .format(job["_jobid"], job["local_directory"]))

    with cd:
        orchestrator_class = ORCHESTRATORS[job["orchestrator"]]
        orc = orchestrator_class(resource, job["submitter"], job,
                                 resurrection=True)
        orc.submitter.submission_id = job.get("_submission_id")
    return orc


# Action functions


def show_oneline(job, status=False):
    """Display `job` as a single summary line.
    """
    fmt = "{status}{j[_jobid]} on {j[resource_name]} via {j[submitter]}$ {cmd}"
    if status:
        try:
            orc = _resurrect_orc(job)
            orc_status = orc.status
            _, queried_status = orc.submitter.status
            if orc_status == queried_status:
                # Drop repeated status (e.g., our and condor's "running").
                queried_status = None
        except Exception as exc:
            lgr.warning(exc_str(exc))
            orc_status = "N/A"
            queried_status = None
        stat = "[status: {}{}] ".format(
            orc_status,
            ", " + queried_status if queried_status else "")
    else:
        stat = ""
    try:
        cmd = job["_resolved_command_str"]
        print(fmt
              .format(status=stat, j=job,
                      cmd=cmd[:47] + "..." if len(cmd) > 50 else cmd))
    except KeyError as exc:
        lgr.warning(
            "Skipping following job record missing %s: %s",
            exc, job
        )


def show(job, status=False):
    """Display detailed information about `job`.
    """
    if status:
        orc = _resurrect_orc(job)
        queried_normalized, queried = orc.submitter.status
        job["status"] = {"orchestrator": orc.status,
                         "queried": queried,
                         "queried_normalized": queried_normalized}
    print(yaml.safe_dump(job))


def fetch(job):
    """Fetch `job` locally.
    """
    orc = _resurrect_orc(job)
    if orc.has_completed:
        orc.fetch()
        LREG.unregister(orc.jobid)
    else:
        lgr.warning("Not fetching incomplete job %s [status: %s]",
                    job["_jobid"],
                    orc.status or "unknown")


class Jobs(Interface):
    """View and manage `reproman run` jobs.

    The possible actions are

      - list: Display a oneline list of all registered jobs

      - show: Display more information for each job over multiple lines

      - delete: Unregister a job locally

      - fetch: Fetch a completed job

      - auto: If jobs are specified (via JOB or --all), behave like 'fetch'.
        Otherwise, behave like 'list'.
    """

    _params_ = dict(
        queries=Parameter(
            metavar="JOB",
            nargs="*",
            doc="""A full job ID or a unique substring."""),
        action=Parameter(
            args=("-a", "--action"),
            constraints=EnsureChoice(
                "auto", "list", "show",
                "delete", "fetch"),
            doc="""Operation to perform on the job(s)."""),
        all_=Parameter(
            dest="all_",
            args=("--all",),
            action="store_true",
            doc="Operate on all jobs"),
        status=Parameter(
            dest="status",
            args=("-s", "--status"),
            action="store_true",
            doc="""Query the resource for status information when listing or
            showing jobs"""),
        # TODO: Add ability to restrict to resource.
    )

    @staticmethod
    def __call__(queries, action="auto", all_=False, status=False):
        job_files = LREG.find_job_files()

        if not job_files:
            lgr.info("No jobs found")
            return

        if all_:
            matched_ids = job_files.keys()
        else:
            matched_ids = []
            for query in queries:
                m = match(query, job_files)
                if m:
                    matched_ids.append(m)
                else:
                    lgr.warning("No jobs matched query %s", query)

        if not matched_ids and action in ["delete", "fetch"]:
            # These are actions where we don't want to just conveniently
            # default to "all" unless --all is explicitly specified.
            raise ValueError("Must specify jobs to {}".format(action))

        # We don't need to load the job to delete it, so check that first.
        if action == "delete":
            for i in matched_ids:
                LREG.unregister(i)
        else:
            jobs = [_load(job_files[i]) for i in matched_ids or job_files]

            if action == "fetch" or (action == "auto" and matched_ids):
                fn = fetch
            elif action == "list" or action == "auto":
                fn = partial(show_oneline, status=status)
            elif action == "show":
                fn = partial(show, status=status)
            else:
                raise RuntimeError("Unknown action: {}".format(action))

            for job in jobs:
                try:
                    fn(job)
                except OrchestratorError as exc:
                    lgr.error("job %s failed: %s", job["_jobid"], exc_str(exc))
                except ResourceNotFoundError:
                    lgr.error("Resource %s (%s) no longer exists",
                              job["resource_id"], job["resource_name"])
