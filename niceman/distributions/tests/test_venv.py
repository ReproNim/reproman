# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import os
import sys

from appdirs import AppDirs
import attr
import pytest

from niceman.cmd import Runner
from niceman.utils import chpwd
from niceman.tests.utils import create_pymodule
from niceman.tests.utils import skip_if_no_network, assert_is_subset_recur
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
