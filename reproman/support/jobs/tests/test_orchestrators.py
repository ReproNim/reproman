# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
import os
import os.path as op
import yaml

from unittest.mock import MagicMock
from unittest.mock import patch
import pytest

from reproman.consts import TEST_SSH_DOCKER_DIGEST
from reproman.utils import chpwd
from reproman.utils import swallow_logs
from reproman.resource.shell import Shell
from reproman.support.exceptions import MissingExternalDependency
from reproman.support.exceptions import OrchestratorError
from reproman.support.external_versions import external_versions
from reproman.support.jobs import orchestrators as orcs
from reproman.tests.fixtures import get_docker_fixture
from reproman.tests.skip import mark
from reproman.tests.skip import skipif
from reproman.tests.utils import create_tree


try:
    lsf_config = os.environ['REPROMAN_LSF_TEST_CONFIG'].split(':')
    lsf_config = {"host": lsf_config[0],
                  "user": lsf_config[1],
                  "tmpdir_root": lsf_config[2]}
except (KeyError, ValueError):
    lsf_config = None


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


@pytest.fixture(scope="module")
def ssh():
    skipif.no_ssh()
    from reproman.resource.ssh import SSH
    return SSH("testssh", host="reproman-test")


@pytest.fixture(scope="module")
def ssh_slurm():
    skipif.no_ssh()
    skipif.no_slurm()
    from reproman.resource.ssh import SSH
    return SSH("slurm-res", host="slurm")


@pytest.fixture(scope="module")
def ssh_lsf():
    skipif.no_ssh()
    if not lsf_config:
        pytest.skip("no LSF test configuration")
    from reproman.resource.ssh import SSH
    return SSH("lsf-res", host=lsf_config["host"], user=lsf_config["user"])


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
            "inputs": [op.join("d", "in")],
            "outputs": ["out"],
            "_resolved_command_str": 'bash -c "cat d/in >out && echo more >>out"'}


@pytest.fixture()
def check_orc_plain(tmpdir):
    local_dir = str(tmpdir)

    def fn(resource, jspec):
        create_tree(local_dir, {"d": {"in": "content\n"}})
        with chpwd(local_dir):
            orc = orcs.PlainOrchestrator(resource, submission_type="local",
                                         job_spec=jspec)
            orc.prepare_remote()
            assert orc.session.exists(
                op.join(orc.working_directory, "d", "in"))

            orc.submit()
            orc.follow()
            assert orc.session.exists(op.join(orc.working_directory, "out"))

            orc.fetch()
            assert open("out").read() == "content\nmore\n"

            metadir_local = op.relpath(orc.meta_directory,
                                       orc.working_directory)
            for fname in "status", "stderr", "stdout":
                assert op.exists(op.join(metadir_local, fname + ".0"))
    return fn


def test_orc_plain_shell(check_orc_plain, shell, job_spec):
    check_orc_plain(shell, job_spec)


def test_orc_resurrection_invalid_job_spec(check_orc_plain, shell):
    with pytest.raises(OrchestratorError):
        orcs.PlainOrchestrator(shell, submission_type="local",
                               job_spec={}, resurrection=True)


@pytest.mark.integration
def test_orc_plain_docker(check_orc_plain, docker_resource, job_spec):
    job_spec["root_directory"] = "/root/nm-run"
    check_orc_plain(docker_resource, job_spec)


@pytest.mark.integration
def test_orc_plain_ssh(check_orc_plain, ssh, job_spec):
    check_orc_plain(ssh, job_spec)


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


@pytest.fixture()
def dataset(tmpdir_factory):
    skipif.no_datalad()
    import datalad.api as dl
    path = str(tmpdir_factory.mktemp("dataset"))
    ds = dl.Dataset(path).create(force=True)

    create_tree(ds.path, {"foo": "foo",
                          "bar": "bar",
                          "d": {"in": "content\n"}})
    ds.save()
    ds.repo.tag("root")
    return ds


@pytest.fixture(scope="module")
def container_dataset(tmpdir_factory):
    skipif.no_datalad()
    skipif.no_network()

    if "datalad_container" not in external_versions:
        pytest.skip("datalad-container not installed")

    import datalad.api as dl
    path = str(tmpdir_factory.mktemp("container_dataset"))
    ds = dl.Dataset(path).create(force=True)
    ds.containers_add(
        "dc",
        url="shub://datalad/datalad-container:testhelper")
    return ds


@pytest.fixture()
def check_orc_datalad(job_spec, dataset):
    def fn(resource, orc_class, sub_type, job_params=None):
        repo = dataset.repo
        repo.tag("start-pt")
        branch_orig = repo.get_active_branch()

        if job_params:
            for k, v in job_params.items():
                job_spec[k] = v

        def run_and_check(spec):
            with chpwd(dataset.path):
                orc = orc_class(resource,
                                submission_type=sub_type, job_spec=spec)
                orc.prepare_remote()
                orc.submit()
                orc.follow()

                orc.fetch()
                assert repo.file_has_content("out")
                assert open("out").read() == "content\nmore\n"
                return orc

        if sub_type == "lsf":
            # for the LSF test, reroot the remote temporary directory
            # under the directory given in REPROMAN_LSF_TEST_CONFIG
            rel_dir = op.relpath(job_spec["root_directory"], "/")
            new_root_directory = op.join(lsf_config["tmpdir_root"], rel_dir)
            job_spec["root_directory"] = new_root_directory

        orc = run_and_check(job_spec)

        # Perform another run based on the dumped job spec from the first.
        assert repo.get_active_branch() == branch_orig
        metadir = op.relpath(orc.meta_directory, orc.working_directory)
        with open(op.join(dataset.path, metadir, "spec.yaml")) as f:
            dumped_spec = yaml.safe_load(f)
            assert "_reproman_version" in dumped_spec
            assert "_spec_version" in dumped_spec

        with open(op.join(dataset.path, metadir, "submit")) as f:
            submit_contents = f.read()
            if job_spec.get("launcher") == "true":
                assert "LAUNCHER" in submit_contents
            else:
                assert "LAUNCHER" not in submit_contents

        if orc.name == "datalad-local-run":
            # Our reproman-based copying of data doesn't isn't (yet) OK with
            # data files that already exist.
            dumped_spec["inputs"] = []
        repo.call_git(["checkout", "-b", "other", "start-pt"])
        if repo.dirty:
            # The submitter log file is ignored (currently only relevant for
            # condor; see b9277ebc0 for more details). Add the directory to get
            # to a clean state.
            dataset.save(".reproman")
        orc = run_and_check(dumped_spec)
    return fn


@pytest.mark.integration
@pytest.mark.parametrize("orc_class",
                         [orcs.DataladLocalRunOrchestrator,
                          orcs.DataladPairRunOrchestrator],
                         ids=["orc:local", "orc:pair"])
@pytest.mark.parametrize("sub_type",
                         ["local",
                          pytest.param("condor", marks=mark.skipif_no_condor)],
                         ids=["sub:local", "sub:condor"])
def test_orc_datalad_run(check_orc_datalad, shell, orc_class, sub_type):
    check_orc_datalad(shell, orc_class, sub_type)


@pytest.mark.integration
@pytest.mark.parametrize("launcher", [False, True],
                         ids=["no launcher", "launcher=true"])
def test_orc_datalad_slurm(check_orc_datalad, ssh_slurm, launcher):
    check_orc_datalad(ssh_slurm, orcs.DataladLocalRunOrchestrator, "slurm",
                      job_params={"launcher": "true"} if launcher else None)


@pytest.mark.integration
def test_orc_datalad_lsf(check_orc_datalad, ssh_lsf):
    check_orc_datalad(ssh_lsf, orcs.DataladLocalRunOrchestrator, "lsf")


@pytest.mark.integration
def test_orc_datalad_run_change_head(job_spec, dataset, shell):
    with chpwd(dataset.path):
        orc = orcs.DataladLocalRunOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()

        create_tree(dataset.path, {"sinceyouvebeengone":
                                   "imsomovingon,yeahyeah"})
        dataset.save()

        orc.fetch()
        ref = "refs/reproman/{}".format(orc.jobid)
        assert not dataset.repo.is_ancestor(ref, "HEAD")

        with orcs.head_at(dataset, ref):
            assert dataset.repo.file_has_content("out")
            assert open("out").read() == "content\nmore\n"


@pytest.mark.parametrize("failed",
                         [[0],
                          [0, 10],
                          list(range(10))],
                         # ATTN: The id function needs to return a string until
                         # pytest v4.2.1 (specifically 4c7ddb8d9).
                         ids=lambda x: str(len(x)))
def test_orc_log_failed(failed):
    nfailed = len(failed)
    with swallow_logs(new_level=logging.INFO) as log:
        orcs.Orchestrator._log_failed("jid", "metadir", failed)
        assert "{} subjob".format(nfailed) in log.out
        assert "jid stderr:" in log.out
        if nfailed > 6:
            assert "stderr.*" in log.out
        elif nfailed == 1:
            assert "stderr.{}".format(failed[0]) in log.out
        else:
            assert "stderr.{" in log.out


@pytest.mark.integration
def test_orc_plain_failure(tmpdir, job_spec, shell):
    job_spec["_resolved_command_str"] = "iwillfail"
    job_spec["inputs"] = []
    local_dir = str(tmpdir)
    with chpwd(local_dir):
        orc = orcs.PlainOrchestrator(shell, submission_type="local",
                                     job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()
    for fname in "status", "stderr", "stdout":
        assert op.exists(op.join(orc.meta_directory, fname + ".0"))


@pytest.mark.integration
def test_orc_datalad_run_failed(job_spec, dataset, ssh):
    job_spec["_resolved_command_str"] = "iwillfail"
    job_spec["inputs"] = []

    with chpwd(dataset.path):
        orc = orcs.DataladPairRunOrchestrator(
            ssh, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()
        with swallow_logs(new_level=logging.INFO) as log:
            orc.fetch()
            assert "1 subjob failed" in log.out
            assert "stderr:" in log.out


@pytest.mark.integration
def test_orc_datalad_pair_run_multiple_same_point(job_spec, dataset, ssh):
    # Start two orchestrators from the same point:
    #
    #   orc 0, <branch tip>
    #   |
    #   | orc 1
    #   |/
    #   o
    ds = dataset
    repo = ds.repo
    branch_orig = repo.get_active_branch()

    js0 = job_spec
    js1 = dict(job_spec, _resolved_command_str='bash -c "echo other >other"')
    with chpwd(ds.path):
        orc0, orc1 = [
            orcs.DataladPairRunOrchestrator(ssh, submission_type="local",
                                            job_spec=js)
            for js in [js0, js1]]

        for orc in [orc0, orc1]:
            orc.prepare_remote()
            orc.submit()
            orc.follow()

        # The status for the first one is now out-of-tree ...
        assert not op.exists(op.join(orc0.meta_directory, "status.0"))
        # but we can still get it.
        assert orc0.status == "succeeded"

        orc0.fetch()
        orc1.fetch()

        ref0 = "refs/reproman/{}".format(orc0.jobid)
        ref1 = "refs/reproman/{}".format(orc1.jobid)
        assert not repo.is_ancestor(ref0, ref1)
        assert not repo.is_ancestor(ref1, ref0)

        # Both runs branched off of the original branch. The first one fetched
        # advanced it. The other one is a side-branch.
        assert not repo.is_ancestor(ref1, "HEAD")
        assert repo.get_hexsha(ref0) == repo.get_hexsha(branch_orig)
        assert repo.get_active_branch() == branch_orig


@pytest.mark.integration
def test_orc_datalad_pair_run_ontop(job_spec, dataset, ssh):
    # Run one orchestrator and fetch, then run another and fetch:
    #
    #   orc 1, <branch tip>
    #   |
    #   o orc 0
    #   |
    #   o
    ds = dataset
    repo = ds.repo
    branch_orig = repo.get_active_branch()

    create_tree(ds.path, {"in": "content\n"})
    ds.save()

    js0 = job_spec
    js1 = dict(job_spec, _resolved_command_str='bash -c "echo other >other"')
    with chpwd(ds.path):
        def do(js):
            orc = orcs.DataladPairRunOrchestrator(
                ssh, submission_type="local", job_spec=js)
            orc.prepare_remote()
            orc.submit()
            orc.follow()
            orc.fetch()
            return orc

        orc0 = do(js0)
        orc1 = do(js1)

        ref0 = "refs/reproman/{}".format(orc0.jobid)
        ref1 = "refs/reproman/{}".format(orc1.jobid)

        assert repo.is_ancestor(ref0, ref1)
        assert repo.get_hexsha(ref0) != repo.get_hexsha(ref1)
        assert repo.get_hexsha(ref1) == repo.get_hexsha(branch_orig)
        assert repo.get_active_branch() == branch_orig


@pytest.mark.integration
def test_orc_datalad_run_results_missing(job_spec, dataset, shell):
    with chpwd(dataset.path):
        orc = orcs.DataladLocalRunOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()
        os.unlink(op.join(orc.root_directory, "outputs",
                          "{}.tar.gz".format(orc.jobid)))
        with pytest.raises(OrchestratorError):
            orc.fetch()


@pytest.mark.xfail(reason="Singularity Hub is down", run=False)
@pytest.mark.integration
@pytest.mark.parametrize("orc_class",
                         [orcs.DataladPairRunOrchestrator,
                          orcs.DataladLocalRunOrchestrator],
                         ids=["orc:pair", "orc:local"])
def test_orc_datalad_run_container(tmpdir, dataset,
                                   container_dataset, shell, orc_class):
    ds = dataset
    ds.install(path="subds", source=container_dataset)
    if orc_class == orcs.DataladLocalRunOrchestrator:
        # We need to have the image locally in order to copy it to the
        # non-dataset remote.
        ds.get(op.join("subds", ".datalad", "environments"))
    with chpwd(ds.path):
        orc = orc_class(
            shell, submission_type="local",
            job_spec={"root_directory": op.join(str(tmpdir), "nm-run"),
                      "outputs": ["out"],
                      "container": "subds/dc",
                      "_resolved_command_str": 'sh -c "ls / >out"'})
        orc.prepare_remote()
        orc.submit()
        orc.follow()
        orc.fetch()
        assert ds.repo.file_has_content("out")
        assert "singularity" in open("out").read()


@pytest.mark.integration
@pytest.mark.parametrize("orc_class",
                         [orcs.DataladPairOrchestrator,
                          orcs.DataladNoRemoteOrchestrator],
                         ids=["orc:pair", "orc:no-remote"])
def test_orc_datalad_nonrun(job_spec, dataset, shell, orc_class):
    with chpwd(dataset.path):
        orc = orc_class(shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()

        orc.fetch()
        assert dataset.repo.is_under_annex("out")
        assert (dataset.pathobj / "out").exists()


@mark.skipif_no_datalad
@pytest.mark.integration
@pytest.mark.parametrize("should_pass", [True, False], ids=["success", "failure"])
def test_orc_datalad_no_remote_get(tmpdir, shell, should_pass):
    import datalad.api as dl

    topdir = str(tmpdir)
    ds_a = dl.create(op.join(topdir, "a"))
    if should_pass:
        (ds_a.pathobj / "foo").write_text("data")
        ds_a.save()

    ds_b = dl.clone(ds_a.path, op.join(topdir, "b"))
    assert not ds_b.repo.file_has_content("foo")
    with chpwd(ds_b.path):
        orc = orcs.DataladNoRemoteOrchestrator(
            shell, submission_type="local",
            job_spec={"root_directory": op.join(topdir, "run-root"),
                      "inputs": ["foo"],
                      "outputs": ["out"],
                      "_resolved_command_str": 'sh -c "cat foo foo >out"'})
        if should_pass:
            orc.prepare_remote()
            orc.submit()
            orc.follow()

            finish_fn = MagicMock()
            orc.fetch(on_remote_finish=finish_fn)
            finish_fn.assert_called_once_with(orc.resource, [])
            assert (ds_b.pathobj / "out").read_text() == "datadata"
        else:
            with pytest.raises(OrchestratorError):
                orc.prepare_remote()


@mark.skipif_no_datalad
@pytest.mark.integration
def test_orc_datalad_no_remote_only_local(dataset, job_spec, ssh):
    with chpwd(dataset.path):
        orc = orcs.DataladNoRemoteOrchestrator(
            ssh, submission_type="local", job_spec=job_spec)
        with pytest.raises(OrchestratorError):
            orc.prepare_remote()


@pytest.mark.integration
def test_orc_datalad_abort_if_dirty(job_spec, dataset, ssh):
    subds = dataset.create(path="sub")
    subds.create(path="subsub")
    dataset.save()

    job_spec["inputs"] = []
    job_spec["outputs"] = []

    def get_orc(jspec=None):
        return orcs.DataladPairRunOrchestrator(
            ssh, submission_type="local",
            job_spec=jspec or job_spec)

    def run(**spec_kwds):
        jspec = dict(job_spec, **spec_kwds)
        with chpwd(dataset.path):
            orc = get_orc(jspec)
            # Run one job so that we create the remote repository.
            orc.prepare_remote()
            orc.submit()
            orc.follow()
            orc.fetch()
            return orc

    with chpwd(dataset.path):
        # We abort if the local dataset is dirty.
        create_tree(dataset.path, {"local-dirt": ""})
        with pytest.raises(OrchestratorError) as exc:
            get_orc()
        assert "dirty" in str(exc.value)
        os.unlink("local-dirt")

    # Run one job so that we create the remote repository.
    run(_resolved_command_str="echo one >one")

    with chpwd(dataset.path):
        orc1 = get_orc()
        create_tree(orc1.working_directory, {"dirty": ""})
        with pytest.raises(OrchestratorError) as exc:
            orc1.prepare_remote()
        assert "dirty" in str(exc.value)
    os.unlink(op.join(orc1.working_directory, "dirty"))

    # We can run if the submodule simply has a different commit checked out.
    run(_resolved_command_str="echo two >two")

    create_tree(op.join(dataset.path, "sub"), {"for-local-commit": ""})
    dataset.save(recursive=True)

    run(_resolved_command_str="echo three >three")

    # But we abort if subdataset is actually dirty.
    with chpwd(dataset.path):
        orc2 = get_orc()
        create_tree(orc2.working_directory,
                    {"sub": {"subsub": {"subdirt": ""}}})
        with pytest.raises(OrchestratorError) as exc:
            orc2.prepare_remote()
        assert "dirty" in str(exc.value)
    os.unlink(op.join(orc2.working_directory, "sub", "subsub", "subdirt"))


def test_orc_datalad_abort_if_detached(job_spec, dataset, shell):
    dataset.repo.checkout("HEAD^{}")

    with chpwd(dataset.path):
        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        with pytest.raises(OrchestratorError):
            orc.prepare_remote()


def test_orc_datalad_resurrect(job_spec, dataset, shell):
    for k in ["_jobid",
              "working_directory", "root_directory", "local_directory"]:
        job_spec[k] = "doesn't matter"
    job_spec["_head"] = "deadbee"
    with chpwd(dataset.path):
        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec,
            resurrection=True)
    assert orc.head == "deadbee"


def test_head_at_dirty(dataset):
    create_tree(dataset.path, {"dirt": ""})
    with pytest.raises(OrchestratorError):
        with orcs.head_at(dataset, "doesntmatter"):
            pass


def test_head_at_unknown_ref(dataset):
    with pytest.raises(OrchestratorError) as exc:
        with orcs.head_at(dataset, "youdontknowme"):
            pass
    assert "youdontknowme" in str(exc.value)


def test_head_at_empty_branch(dataset):
    repo = dataset.repo
    branch_orig = repo.get_active_branch()
    repo.checkout("orph", options=["--orphan"])
    repo.call_git(["reset", "--hard"])
    assert not repo.dirty
    with pytest.raises(OrchestratorError) as exc:
        with orcs.head_at(dataset, branch_orig):
            pass
    assert "No commit" in str(exc.value)


def test_head_at_no_move(dataset):
    repo = dataset.repo
    branch_orig = repo.get_active_branch()
    with orcs.head_at(dataset, branch_orig) as moved:
        assert not moved
        create_tree(dataset.path, {"f0": "on original branch"})
        dataset.save("f0", message="advance branch")
        assert repo.get_active_branch() == branch_orig
    assert repo.get_active_branch() == branch_orig


def test_head_at_move(dataset):
    repo = dataset.repo
    branch_orig = repo.get_active_branch()

    def dataset_path_exists(path):
        return op.exists(op.join(dataset.path, path))

    create_tree(dataset.path, {"pre": "pre"})
    dataset.save("pre")
    with orcs.head_at(dataset, branch_orig + "~1") as moved:
        assert moved
        assert repo.get_active_branch() is None
        assert not dataset_path_exists("pre")
        create_tree(dataset.path, {"at-head": "at-head"})
        dataset.save("at-head",
                     message="advance head (not {})".format(branch_orig))
    assert dataset_path_exists("pre")
    assert not dataset_path_exists("at-head")
    assert repo.get_active_branch() == branch_orig


def test_dataset_as_dict(shell, dataset, job_spec):
    with chpwd(dataset.path):
        orc = orcs.DataladLocalRunOrchestrator(shell, submission_type="local",
                                               job_spec=job_spec)
    d = orc.as_dict()
    # Check for keys that DataladOrchestrator should extend
    # OrchestratorError.asdict() with.
    assert "_head" in d
    assert "_dataset_id" in d


@pytest.fixture()
def check_orc_datalad_concurrent(job_spec, dataset):
    def fn(ssh, orc_class, sub_type, job_params=None):
        names = ["paul", "rosa"]

        job_spec["inputs"] = ["{p[name]}.in"]
        job_spec["outputs"] = ["{p[name]}.out"]
        job_spec["_resolved_command_str"] = "sh -c 'cat {inputs} {inputs} >{outputs}'"
        job_spec["_resolved_batch_parameters"] = [{"name": n} for n in names]
        if job_params:
            for k, v in job_params.items():
                job_spec[k] = v

        in_files = [n + ".in" for n in names]
        for fname in in_files:
            with open(op.join(dataset.path, fname), "w") as fh:
                fh.write(fname[0])
        dataset.save(path=in_files)

        with chpwd(dataset.path):
            orc = orc_class(ssh, submission_type=sub_type, job_spec=job_spec)
            orc.prepare_remote()
            orc.submit()
            orc.follow()
            # Just make sure each fetch() seems to have wired up
            # on_remote_finish. test_run.py tests the actual --follow actions.
            remote_fn = MagicMock()
            orc.fetch(on_remote_finish=remote_fn)
            remote_fn.assert_called_once_with(orc.resource, [])

            out_files = [n + ".out" for n in names]
            for ofile in out_files:
                assert dataset.repo.file_has_content(ofile)
                with open(ofile) as ofh:
                    assert ofh.read() == ofile[0] * 2

            metadir = op.relpath(orc.meta_directory, orc.working_directory)
            for idx in range(len(orc.job_spec["_command_array"])):
                for fname in "status", "stderr", "stdout":
                    assert op.lexists(op.join(metadir, f"{fname}.{idx}"))
    return fn


@pytest.mark.integration
@pytest.mark.parametrize("orc_class",
                         [orcs.DataladLocalRunOrchestrator,
                          orcs.DataladPairOrchestrator,
                          orcs.DataladPairRunOrchestrator],
                         ids=["orc:local-run", "orc:pair-run", "orc-pair"])
@pytest.mark.parametrize("sub_type",
                         ["local",
                          pytest.param("condor", marks=mark.skipif_no_condor)],
                         ids=["sub:local", "sub:condor"])
def test_orc_datalad_concurrent(check_orc_datalad_concurrent,
                                ssh, orc_class, sub_type):
    check_orc_datalad_concurrent(ssh, orc_class, sub_type)


@pytest.mark.integration
@pytest.mark.parametrize("launcher", [False, True],
                         ids=["no launcher", "launcher=true"])
def test_orc_datalad_concurrent_slurm(check_orc_datalad_concurrent, ssh_slurm,
                                      launcher):
    check_orc_datalad_concurrent(ssh_slurm,
                                 orcs.DataladLocalRunOrchestrator,
                                 "slurm",
                                 {"launcher": "true"} if launcher else None)


def test_orc_datalad_pair_submodule(job_spec, dataset, shell):
    # Smoke test that triggers the failure from gh-499
    with chpwd(dataset.path):
        dataset.create("sub")
        dataset.save()

        job_spec["_resolved_command_str"] = "sh -c 'echo foo >sub/foo'"
        job_spec["inputs"] = []
        job_spec["outputs"] = []

        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()
        orc.fetch()


def test_orc_datalad_pair_need_follow_parent(job_spec, dataset, shell):
    # An example of a scenario that fails without DataLad's --follow=parentds
    with chpwd(dataset.path):
        dataset.create("sub")
        dataset.save()

        job_spec["_resolved_command_str"] = "sh -c 'echo baz >baz'"
        job_spec["inputs"] = []
        job_spec["outputs"] = []

        orc0 = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc0.prepare_remote()
        orc0.submit()
        orc0.follow()

        job_spec["_resolved_command_str"] = "sh -c 'echo bar >sub/bar'"
        output = op.join("sub", "bar")
        job_spec["outputs"] = [output]
        orc1 = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc1.prepare_remote()
        orc1.submit()
        orc1.follow()
        orc1.fetch()
        assert op.exists(output)


def test_orc_datalad_pair_submodule_conflict(caplog, job_spec, dataset, shell):
    # In this scenario, one job modifies a submodule, and before that change,
    # another job is launched that modifies the same submodule. This creates a
    # change that can't be brought in with `datalad update` because, even with
    # --follow=parentds, the top-level repo still brings in changes from the
    # remote, whose branch points to the first job. In a diagram, the remote
    # state is:
    #
    #         ---- job 1 (branch)
    #  base --|
    #         ---- job 2 (detached)
    #
    # On fetch of job 2, we merge the job 2 ref. The `datalad update` call
    # fails trying to merge in branch.
    #
    # If this scenario ends up being common enough, we could consider modifying
    # `datalad update` to optionally not try to merge the remote state of the
    # top-level repo.
    with chpwd(dataset.path):
        dataset.create("sub")
        dataset.save()

        job_spec["_resolved_command_str"] = "sh -c 'echo baz >sub/baz'"
        job_spec["inputs"] = []
        job_spec["outputs"] = []

        orc0 = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc0.prepare_remote()
        orc0.submit()
        orc0.follow()

        job_spec["_resolved_command_str"] = "sh -c 'echo bar >sub/bar'"
        orc1 = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc1.prepare_remote()
        orc1.submit()
        orc1.follow()
        # swallow_logs() won't work here because it hard codes the logger and
        # the log message being checked is bubbled up by DataLad.
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            orc1.fetch()
        # TODO(REVIEW THIS) AFAICT datalad has changed the output++++++++++++++++++++++++++++++++++
        assert "update failure in subdataset" in caplog.text
        assert dataset.repo.call_git(["ls-files", "--unmerged"]).strip()


def test_orc_datalad_pair_merge_conflict(job_spec, dataset, shell):
    with chpwd(dataset.path):
        job_spec["_resolved_command_str"] = "sh -c 'echo baz >baz'"
        job_spec["inputs"] = []
        job_spec["outputs"] = []

        orc0 = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc0.prepare_remote()
        orc0.submit()
        orc0.follow()
        # Introduce a conflict.
        (dataset.pathobj / "baz").write_text("different")
        dataset.save()
        with swallow_logs(new_level=logging.WARNING) as logs:
            orc0.fetch()
            assert "Failed to merge in changes" in logs.out
        assert dataset.repo.call_git(["ls-files", "--unmerged"]).strip()


def test_orc_datalad_pair_new_submodule(job_spec, dataset, shell):
    with chpwd(dataset.path):
        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()
        orc.fetch()

        # prepare_remote() doesn't fail when a new subdataset is added after
        # the first run.
        sub = dataset.create("sub")
        dataset.save()

        job_spec["_resolved_command_str"] = "sh -c 'echo a >sub/a'"
        job_spec["inputs"] = []
        job_spec["outputs"] = []

        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        orc.prepare_remote()
        orc.submit()
        orc.follow()
        orc.fetch()
        assert sub.repo.is_under_annex("a")


def test_orc_datalad_pair_existing_remote(job_spec, dataset, shell):
    root_directory = job_spec["root_directory"]
    repo = dataset.repo
    repo.add_remote("localshell", "i-dont-match")
    with chpwd(dataset.path):
        orc = orcs.DataladPairOrchestrator(
            shell, submission_type="local", job_spec=job_spec)
        # If a remote with the resource name exists, we abort if the
        # URL doesn't match the expected target...
        with pytest.raises(OrchestratorError):
            orc.prepare_remote()
        # ... and continue if it does.
        repo.set_remote_url("localshell", orc.working_directory)
        orc.prepare_remote()
