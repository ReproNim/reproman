# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Registry of local jobs.
"""

import collections
import logging
import os
import os.path as op

import yaml

from reproman import cfg

lgr = logging.getLogger("reproman.support.jobs.local_registry")


class LocalRegistry(object):
    """Registry of local jobs.
    """

    def __init__(self, directory=None):
        self._root = directory or op.join(cfg.dirs.user_data_dir, "jobs")

    def find_job_files(self):
        """Return job files for all jobs that are registered locally.

        Returns
        -------
        OrderedDict mapping job ID to job file.
        """
        files = os.listdir(self._root) if op.exists(self._root) else []
        return collections.OrderedDict((f, op.join(self._root, f))
                                       for f in sorted(files))

    def register(self, jobid, kwds):
        """Register a job.

        Parameters
        ----------
        jobid : str
            Full ID of the job.
        kwds : dict
            Values defined here will be dumped to the job file.
        """
        if not op.exists(self._root):
            os.makedirs(self._root)

        job_file = op.join(self._root, jobid)
        if op.exists(job_file):
            raise ValueError("%s is already registered", jobid)

        with open(job_file, "w") as jfh:
            yaml.safe_dump(kwds, jfh)
        lgr.info("Registered job %s", jobid)

    def unregister(self, jobid):
        """Unregister a job.

        Parameters
        ----------
        jobid : str
            Full ID of the job.
        """
        job_file = op.join(self._root, jobid)
        if op.exists(job_file):
            lgr.info("Unregistered job %s", jobid)
            os.unlink(job_file)
