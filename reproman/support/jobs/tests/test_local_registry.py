# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os.path as op

import pytest
import yaml

from reproman.support.jobs.local_registry import LocalRegistry


def test_local_registry(tmpdir):
    tmpdir = str(tmpdir)
    lreg = LocalRegistry(directory=op.join(tmpdir, "registry"))

    lreg.register("jobid0", {"value0": "foo", "value1": "bar"})
    files = lreg.find_job_files()
    with open(files["jobid0"]) as yfh:
        loaded = yaml.safe_load(yfh)
        assert "value0" in loaded
        assert "value1" in loaded

    # Can't register same ID.
    with pytest.raises(ValueError):
        lreg.register("jobid0", {})

    lreg.register("jobid1", {"value0": ""})
    files = lreg.find_job_files()
    assert "jobid0" in files
    assert "jobid1" in files

    lreg.unregister("jobid1")
    files = lreg.find_job_files()
    assert "jobid0" in files
    assert "jobid1" not in files
