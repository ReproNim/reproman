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
import sys

from appdirs import AppDirs
import attr
import pytest
import logging

from reproman.cmd import Runner
from reproman.utils import chpwd
from reproman.utils import on_linux
from reproman.utils import swallow_logs
from reproman.tests.utils import create_pymodule
from reproman.tests.utils import assert_is_subset_recur
from reproman.tests.utils import COMMON_SYSTEM_PATH
from reproman.tests.skip import skipif
from reproman.distributions.venv import VenvDistribution
from reproman.distributions.venv import VenvEnvironment
from reproman.distributions.venv import VenvPackage
from reproman.distributions.venv import VenvTracer

PY_VERSION = "python{v.major}.{v.minor}".format(v=sys.version_info)


@pytest.fixture(scope="session")
def venv_test_dir():
    skipif.no_network()
    dirs = AppDirs('reproman')

    ssp = os.getenv("REPROMAN_TESTS_ASSUME_SSP")
    # Encode the SSP value in the directory name so that the caller doesn't
    # have to worry about deleting the cached venvs before setting the flag..
    test_dir = os.path.join(dirs.user_cache_dir,
                            'venv_test{}'.format("_ssp" if ssp else ""))
    if os.path.exists(test_dir):
        return test_dir

    os.makedirs(test_dir)
    pymod_dir = os.path.join(test_dir, "minimal_pymodule")
    create_pymodule(pymod_dir)

    runner = Runner(cwd=test_dir)
    pip0 = op.join("venv0", "bin", "pip")
    pip1 = op.join("venv1", "bin", "pip")
    venv_cmd = [sys.executable, "-m", "virtualenv"]
    runner.run(venv_cmd + ["--python", PY_VERSION, "venv0"])
    runner.run(venv_cmd + ["--python", PY_VERSION, "venv1"])
    runner.run([pip0, "install", "pyyaml"])
    runner.run([pip0, "install", "-e", pymod_dir])
    runner.run([pip1, "install", "attrs"])
    # Pip 21.0 (2021-01-23) dropped python 2 support
    # Make sure we're compatible with older pips, however pip<20.0 does not work with python3
    # specifically, it vendors requests -> urllib3 which imports from collections rather than abc
    # This is the oldest pip we can support.
    runner.run([pip1, "install", "pip==20.0.1"])
    if ssp:
        # The testing environment supports --system_site_packages.
        pip2 = op.join("venv-nonlocal", "bin", "pip")
        runner.run(venv_cmd + ["--python", PY_VERSION,
                               "--system-site-packages", "venv-nonlocal"])
        runner.run([pip2, "install", pymod_dir])

    return test_dir


@pytest.mark.skipif(not on_linux, reason="Test assumes GNU/Linux system")
@pytest.mark.integration
def test_venv_identify_distributions(venv_test_dir):
    libpaths = {p[-1]: os.path.join("lib", PY_VERSION, *p)
                for p in [("abc.py",),
                          ("importlib", "yaml", "machinery.py"),
                          ("site-packages", "yaml", "parser.py"),
                          ("site-packages", "attr", "filters.py")]}

    with chpwd(venv_test_dir):
        path_args = [
            # Both full ...
            os.path.join(venv_test_dir, "venv0", libpaths["parser.py"]),
            # ... and relative paths work.
            os.path.join("venv1", libpaths["filters.py"]),
            # A virtualenv file that isn't part of any particular package.
            os.path.join("venv1", "bin", "pip")
        ]

        expected_unknown = {
            COMMON_SYSTEM_PATH,
            # The editable package was added by VenvTracer as an unknown file.
            os.path.join(venv_test_dir, "minimal_pymodule")}

        # Unknown files do not include "venv0/bin/pip", which is a link to
        # another path within venv0, but they do include links to the system
        # files. However, at some point following Python 3.8.0, such links
        # appear to no longer be present.
        # TODO(asmacdo) it has happened
        abc_path = os.path.join("venv1", libpaths["abc.py"])
        mach_path = os.path.join("venv1", libpaths["machinery.py"])
        if op.exists(abc_path) and op.exists(mach_path):
            path_args.extend([
                # A link to the outside world ...
                abc_path,
                # or in a directory that is a link to the outside world.
                mach_path])
            expected_unknown.add(op.realpath(abc_path))
            expected_unknown.add(op.realpath(mach_path))
        path_args.append(COMMON_SYSTEM_PATH)

        tracer = VenvTracer()

        dists = list(tracer.identify_distributions(path_args))
        assert len(dists) == 1

        distributions, unknown_files = dists[0]
        assert unknown_files == expected_unknown
        assert len(distributions.environments) == 2

        expect = {"environments":
                  [{"packages": [{"files": [libpaths["parser.py"]],
                                  "name": "PyYAML",
                                  "editable": False},
                                 {"files": [], "name": "nmtest",
                                  "editable": True}],
                    "system_site_packages": False},
                   {"packages": [{"files": [libpaths["filters.py"]],
                                  "name": "attrs",
                                  "editable": False}],
                    "system_site_packages": False}]}
        assert_is_subset_recur(expect, attr.asdict(distributions), [dict, list])


@pytest.mark.skipif(not os.getenv("REPROMAN_TESTS_ASSUME_SSP"),
                    reason=("Will not assume system site packages "
                            "unless REPROMAN_TESTS_ASSUME_SSP is set"))
@pytest.mark.integration
def test_venv_system_site_packages(venv_test_dir):
    with chpwd(venv_test_dir):
        tracer = VenvTracer()
        libpath = op.join("lib", PY_VERSION, "site-packages")
        dists = list(
            tracer.identify_distributions([op.join("venv-nonlocal", libpath)]))
        assert len(dists) == 1
        vdist = dists[0][0]
        # We won't do detailed inspection of this because its structure depends
        # on a system we don't control, but we still want to make sure that
        # VenvEnvironment's system_site_packages attribute is set correctly.
        expect = {"environments": [{"packages": [{"files": [],
                                                  "name": "nmtest"}],
                                    "system_site_packages": True}]}
        assert_is_subset_recur(expect, attr.asdict(vdist), [dict, list])


@pytest.mark.integration
def test_venv_install(venv_test_dir, tmpdir):
    tmpdir = str(tmpdir)
    paths = [
        op.join("lib", PY_VERSION, "site-packages", "yaml", "parser.py"),
        op.join("lib", PY_VERSION, "site-packages", "attr", "filters.py"),
    ]

    tracer = VenvTracer()
    dists = list(
        tracer.identify_distributions(
            [op.join(venv_test_dir, "venv0", paths[0]),
             op.join(venv_test_dir, "venv1", paths[1])]))
    assert len(dists) == 1
    dist = dists[0][0]

    assert len(dist.environments) == 2
    for idx in range(2):
        dist.environments[idx].path = op.join(tmpdir, "venv{}".format(idx))

    dist.initiate(None)
    dist.install_packages()

    dists_installed = list(
        tracer.identify_distributions(
            [op.join(tmpdir, "venv0", paths[0]),
             op.join(tmpdir, "venv1", paths[1])]))
    assert len(dists_installed) == 1
    dist_installed = dists_installed[0][0]

    expect = {"environments":
              [{"packages": [{"name": "PyYAML",
                              "editable": False}],
                "system_site_packages": False},
               {"packages": [{"name": "attrs",
                              "editable": False}],
                "system_site_packages": False}]}
    assert_is_subset_recur(expect, attr.asdict(dist_installed), [dict, list])

    # We don't yet handle editable packages.
    assert any([p.name == "nmtest"
                for e in dist.environments
                for p in e.packages])
    assert not any([p.name == "nmtest"
                    for e in dist_installed.environments
                    for p in e.packages])


@pytest.mark.integration
def test_venv_pyc(venv_test_dir, tmpdir):
    from reproman.api import retrace
    tmpdir = str(tmpdir)
    venv_path = op.join("lib", PY_VERSION, "site-packages", "attr")
    pyc_path = op.join(
        venv_test_dir, "venv1", venv_path, "__pycache__",
        "exceptions.cpython-{v.major}{v.minor}.pyc".format(v=sys.version_info))

    if not op.exists(pyc_path):
        pytest.skip("Expected file does not exist: {}".format(pyc_path))

    distributions, unknown_files = retrace([pyc_path])
    assert not unknown_files
    assert len(distributions) == 1
    expect = {"environments":
              [{"packages": [{"files": [op.join(venv_path, "exceptions.py")],
                              "name": "attrs",
                              "editable": False}]}]}
    assert_is_subset_recur(expect,
                           attr.asdict(distributions[0]), [dict, list])


def test_venv_install_noop():
    dist = VenvDistribution(
        name="venv",
        path="/tmp/doesnt/matter/",
        venv_version="15.1.0",
        environments=[
            VenvEnvironment(
                path="/tmp/doesnt/matter/venv",
                python_version="3.7",
                packages=[
                    VenvPackage(
                        name="imeditable",
                        version="0.1.0",
                        editable=True,
                        local=True)])])
    with swallow_logs(new_level=logging.INFO) as log:
        dist.install_packages()
        assert "No local, non-editable packages found" in log.out
