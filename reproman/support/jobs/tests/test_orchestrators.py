# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os
import os.path as op

from unittest.mock import patch
import pytest

from reproman.consts import TEST_SSH_DOCKER_DIGEST
from reproman.utils import chpwd
from reproman.resource.shell import Shell
from reproman.support.exceptions import MissingExternalDependency
from reproman.support.exceptions import OrchestratorError
from reproman.support.external_versions import external_versions
from reproman.support.jobs import orchestrators as orcs
from reproman.tests.fixtures import get_docker_fixture
from reproman.tests.skip import mark
from reproman.tests.skip import skipif
from reproman.tests.utils import create_tree


docker_container = get_docker_fixture(TEST_SSH_DOCKER_DIGEST,
                                      name="testing-container", scope="module")


@pytest.fixture(scope="module")
def docker_resource(docker_container):
    # TODO: This could be reworked to be included in fixtures.py. It is similar
    # to get_singularity_fixture, which should probably be renamed to include
    # "resource".
    from reproman.resource.docker_container import DockerContainer
    return DockerContainer("testing-container")


@pytest.fixture(scope="module")
def shell():
    return Shell("localshell")


def test_orc_root_directory(shell):
    orc = orcs.PlainOrchestrator(shell, submission_type="local")
    assert orc.root_directory == op.expanduser("~/.reproman/run-root")


@pytest.mark.parametrize("value", [{}, {"HOME": "rel/path"}],
                         ids=["no home", "relative"])
def test_orc_root_directory_error(shell, value):
    orc = orcs.PlainOrchestrator(shell, submission_type="local")
    with patch.object(orc.session, "query_envvars", return_value=value):
        with pytest.raises(OrchestratorError):
            orc.root_directory


@pytest.fixture()
def job_spec(tmpdir):
    return {"root_directory": op.join(str(tmpdir), "nm-run"),
            "inputs": ["in"],
            "outputs": ["out"],
            "command_str": 'bash -c "cat in >out && echo more >>out"'}


@pytest.fixture()
def check_orc_plain(tmpdir):
    local_dir = str(tmpdir)

    def fn(resource, jspec):
        create_tree(local_dir, {"in": "content\n"})
        with chpwd(local_dir):
            orc = orcs.PlainOrchestrator(resource, submission_type="local",
                                         job_spec=jspec)
            orc.prepare_remote()
            assert orc.session.exists(op.join(orc.working_directory, "in"))

            orc.submit()
            orc.follow()
            assert orc.session.exists(op.join(orc.working_directory, "out"))

            orc.fetch()
            assert open("out").read() == "content\nmore\n"
    return fn


def test_orc_plain_shell(check_orc_plain, shell, job_spec):
    check_orc_plain(shell, job_spec)


@pytest.mark.integration
def test_orc_plain_docker(check_orc_plain, docker_resource, job_spec):
    job_spec["root_directory"] = "/root/nm-run"
    check_orc_plain(docker_resource, job_spec)


@pytest.mark.skipif(external_versions["datalad"], reason="DataLad found")
def test_orc_no_datalad(tmpdir, shell):
    with chpwd(str(tmpdir)):
        with pytest.raises(MissingExternalDependency):
            orcs.DataladLocalRunOrchestrator(shell, submission_type="local")


@mark.skipif_no_datalad
def test_orc_no_dataset(tmpdir, shell):
    with chpwd(str(tmpdir)):
        with pytest.raises(OrchestratorError):
            orcs.DataladLocalRunOrchestrator(shell, submission_type="local")


@pytest.fixture(scope="module")
def base_dataset(tmpdir_factory):
    skipif.no_datalad()
    import datalad.api as dl
    path = str(tmpdir_factory.mktemp("dataset"))
    ds = dl.Dataset(path).create(force=True)

    create_tree(ds.path, {"foo": "foo",
                          "bar": "bar"})
    ds.add(".")
    ds.repo.tag("root")
    return ds


@pytest.fixture()
def dataset(base_dataset):
    base_dataset.repo.checkout("master")
    # FIXME: Use expose method once available.
    base_dataset.repo._git_custom_command([],
                                          ["git", "reset", "--hard", "root"])
    for f in base_dataset.repo.untracked_files:
        os.unlink(op.join(base_dataset.path, f))
    assert not base_dataset.repo.dirty
    return base_dataset


@pytest.mark.integration
@pytest.mark.parametrize("orc_class",
                         [orcs.DataladLocalRunOrchestrator,
                          orcs.DataladPairRunOrchestrator],
                         ids=["orc:local", "orc:pair"])
@pytest.mark.parametrize("sub_type",
                         ["local",
                          pytest.param("condor", marks=mark.skipif_no_condor)],
                         ids=["sub:local", "sub:condor"])
def test_orc_datalad_run(job_spec, dataset, shell, orc_class, sub_type):
    create_tree(dataset.path, {"in": "content\n"})
    dataset.add(".")

    with chpwd(dataset.path):
        orc = orc_class(shell, submission_type=sub_type, job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()

        orc.fetch()
        assert dataset.repo.file_has_content("out")
        assert open("out").read() == "content\nmore\n"


@pytest.mark.integration
def test_orc_datalad_run_change_head(job_spec, dataset, shell):
    create_tree(dataset.path, {"in": "content\n"})
    dataset.add(".")

    with chpwd(dataset.path):
        orc = orcs.DataladLocalRunOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()

        create_tree(dataset.path, {"sinceyouvebeengone":
                                   "imsomovingon,yeahyeah"})
        dataset.add(".")

        orc.fetch()
        ref = "refs/reproman/{}".format(orc.jobid)
        assert not dataset.repo.is_ancestor(ref, "HEAD")

        with orcs.head_at(dataset, ref):
            assert dataset.repo.file_has_content("out")
            assert open("out").read() == "content\nmore\n"


@pytest.mark.integration
def test_orc_datalad_pair_run_multiple(job_spec, dataset, shell):
    ds = dataset
    create_tree(ds.path, {"in": "content\n"})
    ds.add(".")

    js0 = job_spec
    js1 = dict(job_spec, command_str='bash -c "echo other >other"')
    with chpwd(ds.path):
        orc0, orc1 = [
            orcs.DataladPairRunOrchestrator(shell, submission_type="local",
                                            job_spec=js)
            for js in [js0, js1]]

        for orc in [orc0, orc1]:
            orc.prepare_remote()
            orc.submit()
            orc.follow()

        # The status for the first one is now out-of-tree ...
        assert not op.exists(op.join(orc0.meta_directory, "status"))
        # but we can still get it.
        assert orc0.status == "succeeded"

        orc0.fetch()
        orc1.fetch()

        ref0 = "refs/reproman/{}".format(orc0.jobid)
        ref1 = "refs/reproman/{}".format(orc1.jobid)
        assert not ds.repo.is_ancestor(ref0, ref1)
        assert not ds.repo.is_ancestor(ref1, ref0)

        # Both runs branched off of master. The first one fetched advanced it.
        # The other one is a side-branch.
        assert not ds.repo.is_ancestor(ref1, "HEAD")
        assert ds.repo.get_hexsha(ref0) == ds.repo.get_hexsha("master")


@pytest.mark.integration
def test_orc_datalad_pair(job_spec, dataset, shell):
    create_tree(dataset.path, {"in": "content\n"})
    dataset.add(".")

    with chpwd(dataset.path):
        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()

        orc.fetch()
        # The local fetch variant doesn't currently get the content, so just
        # check that the file is under annex.
        assert dataset.repo.is_under_annex("out")


@mark.skipif_no_datalad
def test_orc_datalad_abort_if_detached(job_spec, dataset, shell):
    dataset.repo.checkout("HEAD^{}")

    with chpwd(dataset.path):
        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        with pytest.raises(OrchestratorError):
            orc.prepare_remote()


def test_head_at_dirty(dataset):
    create_tree(dataset.path, {"dirt": ""})
    with pytest.raises(OrchestratorError):
        with orcs.head_at(dataset, "doesntmatter"):
            pass


def test_head_at_unknown_ref(dataset):
    with pytest.raises(OrchestratorError) as exc:
        with orcs.head_at(dataset, "youdontknowme"):
            pass
    assert "youdontknowme" in str(exc)


def test_head_at_empty_branch(dataset):
    dataset.repo.checkout("orph", options=["--orphan"])
    # FIXME: Use expose method once available.
    dataset.repo._git_custom_command([], ["git", "reset", "--hard"])
    assert not dataset.repo.dirty
    with pytest.raises(OrchestratorError) as exc:
        with orcs.head_at(dataset, "master"):
            pass
    assert "No commit" in str(exc)


def test_head_at_no_move(dataset):
    with orcs.head_at(dataset, "master") as moved:
        assert not moved
        create_tree(dataset.path, {"on-master": "on-maser"})
        dataset.add("on-master", message="advance master")
        assert dataset.repo.get_active_branch() == "master"
    assert dataset.repo.get_active_branch() == "master"


def test_head_at_move(dataset):
    def dataset_path_exists(path):
        return op.exists(op.join(dataset.path, path))

    create_tree(dataset.path, {"pre": "pre"})
    dataset.add("pre")
    with orcs.head_at(dataset, "master~1") as moved:
        assert moved
        assert dataset.repo.get_active_branch() is None
        assert not dataset_path_exists("pre")
        create_tree(dataset.path, {"at-head": "at-head"})
        dataset.add("at-head", message="advance head (not master)")
    assert dataset_path_exists("pre")
    assert not dataset_path_exists("at-head")
    assert dataset.repo.get_active_branch() == "master"
