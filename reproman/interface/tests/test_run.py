# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Tests for run and jobs interfaces.
"""

import contextlib
import logging
from unittest.mock import patch
import os
import os.path as op
import shutil
import time

import pytest

from reproman.api import jobs
from reproman.api import run
from reproman.interface.run import _combine_batch_params
from reproman.interface.run import _combine_job_specs
from reproman.interface.run import _resolve_batch_parameters
from reproman.utils import chpwd
from reproman.utils import swallow_logs
from reproman.utils import swallow_outputs
from reproman.support.exceptions import (
    OrchestratorError,
    ResourceNotFoundError,
    JobError,
)
from reproman.tests import fixtures
from reproman.tests.utils import create_tree

lgr = logging.getLogger("reproman.interface.tests.test_run")

# Tests that do not require a resource, registry, or orchestrator.


@pytest.mark.parametrize("command", [None, []],
                         ids=["None", "[]"])
def test_run_no_command(command):
    with pytest.raises(ValueError) as exc:
        run(command=command)
    assert "No command" in str(exc.value)


def test_run_no_resource():
    with pytest.raises(ValueError) as exc:
        run(command="blahbert")
    assert "No resource" in str(exc.value)


@pytest.mark.parametrize("arg,expected",
                         [("", ["local", "plain", "message"]),
                          ("submitters", ["local"]),
                          ("orchestrators", ["plain"]),
                          ("parameters", ["message"])])
def test_run_list(arg, expected):
    with swallow_outputs() as output:
        run(list_=arg)
        for e in expected:
            assert e in output.out


@pytest.mark.parametrize(
    "specs,expected",
    [([], {}),
     ([{"a": "a"}, {"b": "b"}],
      {"a": "a", "b": "b"}),
     ([{"a": "a"}, {"a": "A", "b": "b"}],
      {"a": "A", "b": "b"}),
     ([{"a": {"aa": "aa"}}, {"a": "A", "b": "b"}],
      {"a": "A", "b": "b"}),
     ([{"a": {"aa": "aa"}}, {"a": {"aa": "AA"}, "b": "b"}],
      {"a": {"aa": "AA"}, "b": "b"})],
    ids=["empty", "exclusive", "simple-update",
         "mapping-to-atom", "atom-to-mapping"])
def test_combine_specs(specs, expected):
    assert _combine_job_specs(specs) == expected


@pytest.mark.parametrize(
    "params,expected",
    [([], []),
     (["a=1,2"],
      [{"a": "1"}, {"a": "2"}]),
     (["a=1,2", "b=3"],
      [{"a": "1", "b": "3"},
       {"a": "2", "b": "3"}]),
     (["a=1,2", "b=3,4"],
      [{"a": "1", "b": "3"},
       {"a": "1", "b": "4"},
       {"a": "2", "b": "3"},
       {"a": "2", "b": "4"}]),
     (["a=1,2=3"],
      [{"a": "1"},
       {"a": "2=3"}]),
     (["a= 1 spaces are preserved   , 2"],
      [{"a": " 1 spaces are preserved   "},
       {"a": " 2"}])],
    ids=["empty", "one", "two, one varying", "two varying", "= in value",
         "spaces"])
def test_combine_batch_params(params, expected):
    actual = list(sorted(_combine_batch_params(params),
                         key=lambda d: (d.get("a"), d.get("b"))))
    assert len(actual) == len(expected)
    assert actual == expected


def test_combine_batch_params_glob(tmpdir):
    tmpdir = str(tmpdir)
    create_tree(tmpdir, {"aaa": "a",
                         "subdir": {"b": "b", "c": "c"}})
    with chpwd(tmpdir):
        res = sorted(_combine_batch_params(["foo=a*,subdir/*,other"]),
                     key=lambda d: d["foo"])
        assert list(res) == [
            {"foo": "aaa"},
            {"foo": "other"},
            {"foo": "subdir/b"},
            {"foo": "subdir/c"}]


def test_combine_batch_params_repeat_key():
    with pytest.raises(ValueError):
        list(_combine_batch_params(["a=1", "a=2"]))


def test_combine_batch_params_no_equal():
    with pytest.raises(ValueError):
        list(_combine_batch_params(["a"]))


def test_run_batch_spec_and_params():
    with pytest.raises(ValueError):
        run(command="blahbert",
            batch_spec="anything", batch_parameters="anything")


@pytest.mark.parametrize(
    "params,spec",
    [([], ""),
     (["a=1,2"],
      """\
- a: '1'
- a: '2'"""),
     (["a=1,2", "b=3"],
      """\
- a: '1'
  b: '3'
- a: '2'
  b: '3'""")],
    ids=["empty", "one", "two, one varying"])
def test_resolve_batch_params_eq(tmpdir, params, spec):
    fname = op.join(str(tmpdir), "spec.yml")
    with open(fname, "w") as fh:
        fh.write(spec)
    from_param_str = _resolve_batch_parameters(spec_file=None, params=params)
    from_spec = _resolve_batch_parameters(spec_file=fname, params=None)
    assert from_param_str == from_spec


# Tests that require `context`.


job_registry = fixtures.job_registry_fixture()
resource_manager = fixtures.resource_manager_fixture(scope="function")


@pytest.fixture(scope="function")
def context(tmpdir, resource_manager, job_registry):
    """Fixture that provides context for a test run.

    The return value is a dictionary with the following items:

    - run_fn: `interface.run`, patched so that it uses a local registry and
      temporary resource manager.

    - jobs_fn: `interface.jobs`, patched so that it uses the same local
      registry and resource manager as run_fn.

    - registry: a LocalRegistry instance.

    - directory: temporary path that is the current directory when run_fn is
      called.
    """
    home = str(tmpdir)
    path = op.join(home, "local")
    os.makedirs(path, exist_ok=True)

    def run_fn(*args, **kwargs):
        with contextlib.ExitStack() as stack:
            stack.enter_context(chpwd(path))
            # Patch home to avoid populating testing machine with jobs when
            # using local shell.
            stack.enter_context(patch.dict(os.environ, {"HOME": home}))
            stack.enter_context(patch("reproman.interface.run.get_manager",
                                      return_value=resource_manager))
            stack.enter_context(patch("reproman.interface.run.LocalRegistry",
                                      job_registry))
            return run(*args, **kwargs)

    registry = job_registry()

    def jobs_fn(*args, **kwargs):
        with patch("reproman.interface.jobs.get_manager",
                   return_value=resource_manager):
            with patch("reproman.interface.jobs.LREG", registry):
                return jobs(*args, **kwargs)

    return {"directory": path,
            "registry": registry,
            "resource_manager": resource_manager,
            "run_fn": run_fn,
            "jobs_fn": jobs_fn}


def test_run_resource_specification(context):
    path = context["directory"]
    run = context["run_fn"]

    create_tree(
        path,
        tree={"js0.yaml": "resource_name: name-via-js",
              "js1.yaml": ("resource_id: id-via-js\n"
                           "resource_name: name-via-js")})

    # Can specify name via job spec.
    with pytest.raises(ResourceNotFoundError) as exc:
        run(command=["doesnt", "matter"],
            job_specs=["js0.yaml"])
    assert "name-via-js" in str(exc.value)

    # If job spec as name and ID, ID takes precedence.
    with pytest.raises(ResourceNotFoundError) as exc:
        run(command=["doesnt", "matter"],
            job_specs=["js1.yaml"])
    assert "id-via-js" in str(exc.value)

    # Command-line overrides job spec.
    with pytest.raises(ResourceNotFoundError) as exc:
        run(command=["doesnt", "matter"], resref="fromcli",
            job_specs=["js1.yaml"])
    assert "fromcli" in str(exc.value)


def try_fetch(fetch_fn, ntimes=5):
    """Helper to test asynchronous fetch.
    """
    def try_():
        with swallow_logs(new_level=logging.INFO) as log:
            fetch_fn()
            return "Not fetching incomplete job" not in log.out

    for i in range(1, ntimes + 1):
        succeeded = try_()
        if succeeded:
            break
        else:
            sleep_for = (2 ** i) / 2
            lgr.info("Job is incomplete. Sleeping for %s seconds",
                     sleep_for)
            time.sleep(sleep_for)
    else:
        raise RuntimeError("All fetch attempts failed")


def test_run_and_fetch(context):
    path = context["directory"]
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]

    create_tree(
        path,
        tree={"js0.yaml": ("resource_name: myshell\n"
                           "command_str: 'touch ok'\n"
                           "outputs: ['ok']")})

    run(job_specs=["js0.yaml"])

    with swallow_outputs() as output:
        jobs(queries=[], status=True)
        assert "myshell" in output.out
        assert len(registry.find_job_files()) == 1
        try_fetch(lambda: jobs(queries=[], action="fetch", all_=True))
        assert len(registry.find_job_files()) == 0

    assert op.exists(op.join(path, "ok"))


def test_run_and_follow(context):
    path = context["directory"]
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]

    run(command=["touch", "ok"], outputs=["ok"], resref="myshell",
        follow=True)

    with swallow_logs(new_level=logging.INFO) as log:
        jobs(queries=[])
        assert len(registry.find_job_files()) == 0
        assert "No jobs" in log.out

    assert op.exists(op.join(path, "ok"))


@pytest.mark.parametrize("action",
                         ["stop", "stop-if-success",
                          "delete", "delete-if-success"])
def test_run_and_follow_action(context, action):
    run = context["run_fn"]
    expect = "does not support the 'stop' feature"
    with swallow_logs(new_level=logging.INFO) as log:
        with pytest.raises(JobError) as ecm:
            run(command=["false"], resref="myshell",
                follow=action)
        assert ecm.value.failed == [0]
        if action.endswith("-if-success"):
            assert expect not in log.out
        else:
            assert expect in log.out

    if action != "delete":
        with swallow_logs(new_level=logging.INFO) as log:
            run(command=["true"], resref="myshell",
                follow=action)
            assert expect in log.out

    if action.startswith("delete"):
        resman = context["resource_manager"]
        with pytest.raises(ResourceNotFoundError):
            resman.get_resource("myshell", resref_type="name")


def test_jobs_auto_fetch_with_query(context):
    path = context["directory"]
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]

    run(command=["touch", "ok"], outputs=["ok"], resref="myshell")

    jobfiles = registry.find_job_files()
    assert len(jobfiles) == 1
    jobid = list(jobfiles.keys())[0]
    with swallow_outputs():
        try_fetch(lambda: jobs(queries=[jobid[3:]]))
    assert len(registry.find_job_files()) == 0
    assert op.exists(op.join(path, "ok"))


def test_jobs_query_unknown(context):
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]

    run(command=["doesntmatter"], resref="myshell")

    jobfiles = registry.find_job_files()
    assert len(jobfiles) == 1
    jobid = list(jobfiles.keys())[0]
    with swallow_logs(new_level=logging.WARNING) as log:
        jobs(queries=[jobid + "-trailing-garbage"])
        assert "No jobs matched" in log.out
    assert len(registry.find_job_files()) == 1


def test_jobs_delete(context):
    path = context["directory"]
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]

    run(command=["touch", "ok"], outputs=["ok"], resref="myshell")

    # Must explicit specify jobs to delete.
    with pytest.raises(ValueError):
        jobs(queries=[], action="delete")

    jobfiles = registry.find_job_files()
    assert len(jobfiles) == 1
    jobid = list(jobfiles.keys())[0]
    with swallow_outputs():
        jobs(queries=[jobid[3:]], action="delete")
    assert len(registry.find_job_files()) == 0
    assert not op.exists(op.join(path, "ok"))


def test_jobs_show(context):
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]

    run(command=["touch", "ok"], outputs=["ok"], resref="myshell")
    assert len(registry.find_job_files()) == 1

    with swallow_outputs() as output:
        jobs(queries=[], action="show", status=True)
        # `show`, as opposed to `list`, is detailed, multiline display.
        assert len(output.out.splitlines()) > 1
        assert "myshell" in output.out
        assert "status:" in output.out


def test_jobs_unknown_action(context):
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    run(command=["doesntmatter"], resref="myshell")
    with pytest.raises(RuntimeError):
        jobs(queries=[], action="you don't know me")


def test_jobs_ambig_id_match(context):
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]

    run(command=["doesntmatter0"], resref="myshell")
    run(command=["doesntmatter1"], resref="myshell")

    jobfiles = registry.find_job_files()
    assert len(jobfiles) == 2
    jobid0, jobid1 = jobfiles.keys()

    # Start of ID is year, so first characters should be the same.
    assert jobid0[0] == jobid1[0], "test assumption is wrong"

    with pytest.raises(ValueError) as exc:
        jobs(queries=[jobid0[0], jobid1[0]])
    assert "matches multiple jobs" in str(exc.value)


def test_jobs_deleted_resource(context):
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]
    resman = context["resource_manager"]

    resman.create("todelete", resource_type="shell")

    run(command=["doesntmatter0"], resref="todelete")
    run(command=["doesntmatter1"], resref="myshell")

    resman.delete(resman.get_resource("todelete"))

    jobfiles = registry.find_job_files()
    assert len(jobfiles) == 2

    with swallow_outputs() as output:
        with swallow_logs(new_level=logging.ERROR) as log:
            jobs(queries=[], status=True)
            assert "todelete" in log.out
            # The deleted resource won't be there
            assert "todelete" not in output.out
            # ... but the alive one will.
            assert "myshell" in output.out


def test_jobs_deleted_local_directory(context):
    path = context["directory"]
    run = context["run_fn"]
    jobs = context["jobs_fn"]

    run(command=["touch", "ok"], outputs=["ok"], resref="myshell")
    shutil.rmtree(path)
    with swallow_logs(new_level=logging.ERROR) as log:
        jobs(queries=[], status=True)
        assert "no longer exists" in log.out


def test_jobs_orc_error(context):
    run = context["run_fn"]
    jobs = context["jobs_fn"]
    registry = context["registry"]

    run(command=["doesntmatter1"], resref="myshell")

    jobfiles = registry.find_job_files()
    assert len(jobfiles) == 1

    with swallow_outputs() as output:
        with swallow_logs(new_level=logging.ERROR) as log:
            def die_orc(*args, **kwargs):
                raise OrchestratorError("resurrection failed")

            with patch("reproman.interface.jobs.show_oneline",
                       side_effect=die_orc):
                jobs(queries=[], status=True)
            assert "myshell" not in output.out
            assert "resurrection failed" in log.out
