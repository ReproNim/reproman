# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Submitters for `reproman run`.
"""

import abc
import collections
from functools import wraps
import json
import logging
import math
import re
import time

from reproman.cmd import CommandError
from reproman.dochelpers import borrowdoc


lgr = logging.getLogger("reproman.support.jobs.submitters")


def assert_submission_id(method):
    """Decorate `method` to guard against unset submission ID.
    """

    @wraps(method)
    def wrapped(self, *args, **kwds):
        if not self.submission_id:
            lgr.warning("Cannot check status without a submission ID")
            return "unknown", None
        return method(self, *args, **kwds)
    return wrapped


class Submitter(object, metaclass=abc.ABCMeta):
    """Base Submitter class.

    A submitter is responsible for submitting a command on a resource (e.g., to
    a batch system).
    """

    def __init__(self, session):
        self.session = session
        self.submission_id = None

    @abc.abstractproperty
    def submit_command(self):
        """A list the defines the command used to submit the job.
        """

    def submit(self, script, submit_command=None):
        """Submit `script`.

        Parameters
        ----------
        script : str
            Submission script.
        submit_command : list or None, optional
            If specified, use this instead of `.submit_command`.

        Returns
        -------
        submission ID (str) or, if one can't be determined, None.
        """
        lgr.info("Submitting %s", script)
        out, _ = self.session.execute_command(
            (submit_command or self.submit_command) + [script])
        subm_id = out.rstrip()
        if subm_id:
            self.submission_id = subm_id
            return subm_id

    @abc.abstractproperty
    def status(self):
        """Return the status of a submitted job.

        The return value is a tuple where the first item is a restricted set of
        values that the submitter uses to decide what to do. Valid values are
        'waiting', 'completed', and 'unknown'.

        The second item should be the status as reported by the batch system or
        None of one could not be determined.
        """

    def follow(self):
        """Follow submitted command, exiting once it is finished.
        """
        # Sleeping and announcement to the user would follow different
        # time interval.  We will not re-announce unless at least 10 seconds or
        # 10% of the overall waiting time has passed. At the same time
        # we will keep increasing sleep time according to the log of the past
        # time but no longer than 10 sec
        t0 = time.time()
        next_announce = t0
        while True:
            our_status, their_status = self.status
            if our_status != "waiting":
                if their_status:
                    lgr.info("Final state of job %s: %s",
                             self.submission_id, their_status)
                break
            t = time.time()
            dt = (t - t0)
            if t >= next_announce:
                next_announce = t + max(5, dt*1.1)
                lgr.info("Waiting on job %s: %s. Next heartbeat in %d seconds",
                         self.submission_id, their_status, next_announce - t)
            # for dt=0sec, no sleep at all but then grows
            sleep_time = min(10, math.log2(1 + dt))
            lgr.debug("Sleeping for %.2f sec before next check", sleep_time)
            time.sleep(sleep_time)


class PbsSubmitter(Submitter):
    """Submit a PBS job.
    """

    name = "pbs"

    def __init__(self, session):
        super(PbsSubmitter, self).__init__(session)

    @property
    @borrowdoc(Submitter)
    def submit_command(self):
        return ["qsub"]

    @property
    @assert_submission_id
    @borrowdoc(Submitter)
    def status(self):
        # FIXME: One problem is that Torque PBS may not represent the array
        # consistently between versions (or perhaps configuration?). One system
        # I try has [] in the name and allows qstat querying of the commands as
        # a whole, while the other explodes them all out into individual jobs
        # with no way AFAICS to query individual jobs. Going through DRMAA
        # might help in many cases (and is probably something we should
        # provide), but it's not a complete solution because a PBS system we
        # want to support doesn't have DRMAA support.

        # FIXME: Is there a reliable, long-lived way to see a job after it's
        # completed?  (tracejob can fail with permission issues.)
        try:
            stat_out, _ = self.session.execute_command(
                "qstat -f {}".format(self.submission_id))
        except CommandError:
            return "unknown", None

        match = re.search(r"job_state = ([A-Z])", stat_out)
        if not match:
            lgr.warning("No job status match found in %s", stat_out)
            return "unknown", None

        job_state = match.group(1)
        if job_state in ["R", "E", "H", "Q", "W"]:
            our_state = "waiting"
        elif job_state == "C":
            our_state = "completed"
        else:
            our_state = "unknown"
        return our_state, job_state


class CondorSubmitter(Submitter):
    """Submit a HTCondor job.
    """
    name = "condor"

    def __init__(self, session):
        super(CondorSubmitter, self).__init__(session)
        self._status_method = self._status_json

    @property
    @borrowdoc(Submitter)
    def submit_command(self):
        return ["condor_submit", "-terse"]

    @borrowdoc(Submitter)
    def submit(self, script, submit_command=None):
        # Discard return value, which isn't submission ID for the current
        # condor_submit form.
        out = super(CondorSubmitter, self).submit(script, submit_command)
        # Output example (3 subjobs): 199.0 - 199.2
        job_id = out.strip().split(" - ")[0].split(".")[0]
        self.submission_id = job_id
        return job_id

    @property
    @assert_submission_id
    @borrowdoc(Submitter)
    def status(self):
        try:
            st = self._status_method()
        except CommandError:
            if self._status_method.__name__ == "_status_json":
                lgr.debug("condor_q -json failed. Trying another method.")
                self._status_method = self._status_no_json
                st = self._status_method()
            else:
                st = "unknown", None
        return st

    def _status_json(self):
        stat_out, _ = self.session.execute_command(
            "condor_q -json {}".format(self.submission_id))

        if not stat_out.strip():
            lgr.debug("Status output for %s empty", self.submission_id)
            return "unknown", None

        stat_json = json.loads(stat_out)

        # http://pages.cs.wisc.edu/~adesmet/status.html
        condor_states = {0: "unexpanded",
                         1: "idle",
                         2: "running",
                         3: "removed",
                         4: "completed",
                         5: "held",
                         6: "submission error"}

        codes = [sj.get("JobStatus") for sj in stat_json]
        waiting_states = [0, 1, 2, 5]
        if any(c in waiting_states for c in codes):
            our_status = "waiting"
        elif all(c == 4 for c in codes):
            our_status = "completed"
        else:
            our_status = "unknown"
        # FIXME: their status should represent all subjobs, but right now we're
        # just taking the first code.
        return our_status, condor_states.get(codes[0])

    def _status_no_json(self):
        """Unclever status for older condor versions without 'condor_q -json'.
        """
        # Parse the trailing:
        # 0 jobs; 0 completed, 0 removed, 0 idle, 0 running, 0 held, 0 suspended
        stat_out, _ = self.session.execute_command(
            "condor_q {}".format(self.submission_id))
        last_line = stat_out.strip().splitlines()[-1]

        ours, theirs = "unknown", None
        match_njobs = re.match(r"([1-9][0-9]*) jobs;", last_line.strip())
        if match_njobs:
            njobs = int(match_njobs.group(1))

            # Try to match our json matching above. This leaves some out from
            # both lists. I don't know what the exact map is.
            to_ours = [(r"[1-9][0-9]* (idle|running|held)", "waiting"),
                       (r"[1-9][0-9]* (removed)", "unknown"),
                       # Only consider completed if we don't have a hit for
                       # anything else and its number matches the total
                       # reported number of jobs.
                       (r"{} (completed)".format(njobs), "completed")]
            for regexp, ours_ in to_ours:
                match_stat = re.search(regexp, last_line)
                if match_stat:
                    theirs = match_stat.group(1)
                    ours = ours_
                    break
        # FIXME: their status should represent all subjobs, but right now we're
        # just taking the first hit from the list above.
        return ours, theirs


class SlurmSubmitter(Submitter):
    """Submit a Slurm job.
    """
    name = "slurm"

    def __init__(self, session):
        super(SlurmSubmitter, self).__init__(session)

    @property
    @borrowdoc(Submitter)
    def submit_command(self):
        return ["sbatch"]

    @borrowdoc(Submitter)
    def submit(self, script, submit_command=None):
        out = super(SlurmSubmitter, self).submit(script, submit_command)
        # Output example (v19.05): Submitted batch job 5
        job_id = out.strip().split()[-1]
        self.submission_id = job_id
        return job_id

    @property
    @assert_submission_id
    @borrowdoc(Submitter)
    def status(self):
        try:
            stat_out, _ = self.session.execute_command(
                "scontrol show jobid={}".format(self.submission_id))
        except CommandError:
            return "unknown", None

        # Running scontrol with our jobid will show an entry for each subjob.
        matches = re.findall(r"JobState=([A-Z]+)\b", stat_out)
        if not matches:
            lgr.warning("No job status match found in %s", stat_out)
            return "unknown", None

        # https://github.com/SchedMD/slurm/blob/db82f4eb3d844501b53a72ea313a9166d7a421b2/src/common/slurm_protocol_defs.c#L2656
        waiting_states = ["PENDING", "RUNNING"]
        if any(m in waiting_states for m in matches):
            our_state = "waiting"
        elif all(m == "COMPLETED" for m in matches):
            our_state = "completed"
        else:
            our_state = "unknown"
        # FIXME: their status should represent all subjobs, but right now we're
        # just taking the first code.
        return our_state, matches[0]


class LocalSubmitter(Submitter):
    """Submit a local job.
    """

    name = "local"

    def __init__(self, session):
        super(LocalSubmitter, self).__init__(session)

    @property
    @borrowdoc(Submitter)
    def submit_command(self):
        return ["sh"]

    @borrowdoc(Submitter)
    def submit(self, script, submit_command=None):
        out = super(LocalSubmitter, self).submit(script, submit_command)
        pid = None
        if out:
            pid = out.strip() or None
        self.submission_id = pid
        return pid

    @property
    @assert_submission_id
    @borrowdoc(Submitter)
    def status(self):
        try:
            out, _ = self.session.execute_command(
                ["ps", "-o", "pid=", "-p", self.submission_id])
        except CommandError:
            return "unknown", None
        if out.strip():
            status = "waiting", "running"
        else:
            status = "completed", "completed"
        return status


SUBMITTERS = collections.OrderedDict(
    (o.name, o) for o in [
        PbsSubmitter,
        CondorSubmitter,
        SlurmSubmitter,
        LocalSubmitter,
    ]
)
