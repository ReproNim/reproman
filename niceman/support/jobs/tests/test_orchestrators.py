# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os.path as op

from mock import patch
import pytest

from niceman.utils import chpwd
from niceman.resource.shell import Shell
from niceman.support.exceptions import OrchestratorError
from niceman.support.jobs import orchestrators as orcs
from niceman.tests.utils import create_tree


@pytest.fixture(scope="module")
def shell():
    return Shell("localshell")


def test_orc_root_directory(shell):
    orc = orcs.PlainOrchestrator(shell, submission_type="local")
    assert orc.root_directory == op.expanduser("~/.niceman/run-root")


@pytest.mark.parametrize("value", [{}, {"HOME": "rel/path"}],
                         ids=["no home", "relative"])
def test_orc_root_directory_error(shell, value):
    orc = orcs.PlainOrchestrator(shell, submission_type="local")
    with patch.object(orc.session, "query_envvars", return_value=value):
        with pytest.raises(OrchestratorError):
            orc.root_directory


def test_orc_plain(tmpdir, shell):
    tmpdir = str(tmpdir)

    job_spec = {"root_directory": op.join(tmpdir, "nm-run"),
                "inputs": ["in"],
                "outputs": ["out"],
                "command_str": 'bash -c "cat in >out && echo more >>out"'}
    local_dir = op.join(tmpdir, "local")

    create_tree(local_dir, {"in": "content\n"})
    with chpwd(local_dir):
        orc = orcs.PlainOrchestrator(shell, submission_type="local",
                                     job_spec=job_spec)
        orc.prepare_remote()
        assert op.exists(op.join(orc.working_directory, "in"))

        orc.submit()
        orc.submitter.follow()
        assert op.exists(op.join(orc.working_directory, "out"))

        orc.fetch()
        assert open("out").read() == "content\nmore\n"


@pytest.mark.parametrize("run_type", ["local", "pair"])
def test_orc_datalad_run(tmpdir, shell, run_type):
    pytest.importorskip("datalad")
    import datalad.api as dl

    tmpdir = str(tmpdir)

    job_spec = {"root_directory": op.join(tmpdir, "nm-run"),
                "inputs": ["in"],
                "outputs": ["out"],
                "command_str": 'bash -c "cat in >out && echo more >>out"'}
    local_dir = op.join(tmpdir, "local")

    create_tree(local_dir, {"in": "content\n"})
    ds = dl.Dataset(local_dir).create(force=True)
    ds.add(".")

    if run_type == "local":
        orc_class = orcs.DataladLocalRunOrchestrator
    else:
        orc_class = orcs.DataladPairRunOrchestrator

    with chpwd(local_dir):
        orc = orc_class(shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.submitter.follow()

        orc.fetch()
        assert ds.repo.file_has_content("out")
        assert open("out").read() == "content\nmore\n"


def test_orc_datalad_pair(tmpdir, shell):
    pytest.importorskip("datalad")
    import datalad.api as dl

    tmpdir = str(tmpdir)

    job_spec = {"root_directory": op.join(tmpdir, "nm-run"),
                "inputs": ["in"],
                "outputs": ["out"],
                "command_str": 'bash -c "cat in >out && echo more >>out"'}
    local_dir = op.join(tmpdir, "local")

    create_tree(local_dir, {"in": "content\n"})
    ds = dl.Dataset(local_dir).create(force=True)
    ds.add(".")

    with chpwd(local_dir):
        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.submitter.follow()

        orc.fetch()
        # The local fetch variant doesn't currently get the content, so just
        # check that the file is under annex.
        assert ds.repo.is_under_annex("out")
