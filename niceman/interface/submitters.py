# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Submitters for `niceman run`.
"""

import abc
import collections
import json
import logging
import re
import time

import six

from niceman.cmd import CommandError
from niceman.dochelpers import borrowdoc


lgr = logging.getLogger("niceman.interface.submitters")


@six.add_metaclass(abc.ABCMeta)
class Submitter(object):
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
        pass

    def submit(self, script):
        """Submit `script`.

        Parameters
        ----------
        script : str
            Submission script.

        Returns
        -------
        submission ID (str) or, if one can't be determined, None.
        """
        lgr.info("Submitting %s", script)
        subm_id, _ = self.session.execute_command(
            self.submit_command + [script])
        if subm_id:
            self.submission_id = subm_id
            subm_id = subm_id.rstrip()
            return subm_id

    @abc.abstractmethod
    def follow(self):
        """Follow submitted command, exiting once it is finished.
        """
        pass


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

    @borrowdoc(Submitter)
    def follow(self):
        # TODO: Pull out common parts across submitters.

        # FIXME: Is there a reliable, long-lived way to see a job after it's
        # completed?  (tracejob can fail with permission issues.)
        while True:
            try:
                stat_out, _ = self.session.execute_command(
                    "qstat -f {}".format(self.submission_id))
                match = re.search(r"job_state = ([A-Z])", stat_out)
                if not match:
                    break
                job_state = match.group(1)
                lgr.debug("Job %s state: %s", self.submission_id, job_state)
                if job_state != "C":
                    lgr.info("Waiting on job %s", self.submission_id)
                    time.sleep(10)  # TODO: pull out/make configurable
                    continue
            except CommandError:
                pass
            break


class LocalSubmitter(Submitter):
    """Submit a local job.
    """

    # NOTE: At least for testing, this is really local, not "local" as in
    # submission rather than execution node.
    name = "local"

    def __init__(self, session):
        super(LocalSubmitter, self).__init__(session)
        self.proc = None

    def submit_command(self):
        pass

    @borrowdoc(Submitter)
    def submit(self, script):
        import subprocess as sp
        self.proc = sp.Popen([script])
        self.submission_id = str(self.proc.pid)
        return self.submission_id

    @borrowdoc(Submitter)
    def follow(self):
        lgr.info("Waiting on PID %s", self.submission_id)
        self.proc.communicate()


SUBMITTERS = collections.OrderedDict(
    (o.name, o) for o in [
        PbsSubmitter,
        LocalSubmitter,
    ]
)
