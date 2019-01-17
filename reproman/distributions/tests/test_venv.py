# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
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

from niceman.cmd import Runner
from niceman.utils import chpwd
from niceman.tests.utils import create_pymodule
from niceman.tests.utils import skip_if_no_network, assert_is_subset_recur
from niceman.tests.utils import swallow_logs
from niceman.distributions.venv import VenvDistribution
from niceman.distributions.venv import VenvEnvironment
from niceman.distributions.venv import VenvPackage
from niceman.distributions.venv import VenvTracer

PY_VERSION = "python{v.major}.{v.minor}".format(v=sys.version_info)


@pytest.fixture(scope="session")
@skip_if_no_network
def venv_test_dir():
    dirs = AppDirs('niceman')
    test_dir = os.path.join(dirs.user_cache_dir, 'venv_test')
    if os.path.exists(test_dir):
        return test_dir

    runner = Runner()
    runner.run(["mkdir", "-p", test_dir])

    pymod_dir = os.path.join(test_dir, "minimal_pymodule")
    create_pymodule(pymod_dir)

    with chpwd(test_dir):
        runner.run(["virtualenv", "--python", PY_VERSION, "venv0"])
        runner.run(["virtualenv", "--python", PY_VERSION, "venv1"])
        runner.run(["./venv0/bin/pip", "install", "pyyaml"])
        runner.run(["./venv0/bin/pip", "install", "-e", pymod_dir])
        runner.run(["./venv1/bin/pip", "install", "attrs"])
        # Make sure we're compatible with older pips.
        runner.run(["./venv1/bin/pip", "install", "pip==9.0.3"])
    return test_dir


@pytest.mark.integration
def test_venv_identify_distributions(venv_test_dir):
    paths = ["lib/" + PY_VERSION + "/site-packages/yaml/parser.py",
             "lib/" + PY_VERSION + "/site-packages/attr/filters.py"]

    with chpwd(venv_test_dir):
        path_args = [
            # Both full ...
            os.path.join(venv_test_dir, "venv0", paths[0]),
            # ... and relative paths work.
            os.path.join("venv1", paths[1]),
        ]
        path_args.append("/sbin/iptables")

        tracer = VenvTracer()

        dists = list(tracer.identify_distributions(path_args))
        assert len(dists) == 1

        distributions, unknown_files = dists[0]
        assert unknown_files == {
            "/sbin/iptables",
            # The editable package was added by VenvTracer as an unknown file.
            os.path.join(venv_test_dir, "minimal_pymodule")}

        assert len(distributions.environments) == 2

        expect = {"environments":
                  [{"packages": [{"files": [paths[0]], "name": "PyYAML",
                                  "editable": False},
                                 {"files": [], "name": "nmtest",
                                  "editable": True}]},
                   {"packages": [{"files": [paths[1]], "name": "attrs",
                                  "editable": False}]}]}
        assert_is_subset_recur(expect, attr.asdict(distributions), [dict, list])


@pytest.mark.integration
def test_venv_install(venv_test_dir, tmpdir):
    tmpdir = str(tmpdir)
    paths = ["lib/" + PY_VERSION + "/site-packages/yaml/parser.py",
             "lib/" + PY_VERSION + "/site-packages/attr/filters.py"]

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
                              "editable": False}]},
               {"packages": [{"name": "attrs",
                              "editable": False}]}]}
    assert_is_subset_recur(expect, attr.asdict(dist_installed), [dict, list])

    # We don't yet handle editable packages.
    assert any([p.name == "nmtest"
                for e in dist.environments
                for p in e.packages])
    assert not any([p.name == "nmtest"
                    for e in dist_installed.environments
                    for p in e.packages])


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
