# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import os
from subprocess import call
import sys

from appdirs import AppDirs
import attr
import pytest

from niceman.tests.utils import skip_if_no_network, assert_is_subset_recur
from niceman.distributions.venv import VenvTracer


@pytest.fixture(scope="session")
@skip_if_no_network
def venv_test_dir():
    dirs = AppDirs('niceman')
    test_dir = os.path.join(dirs.user_cache_dir, 'venv_test')
    if os.path.exists(test_dir):
        return test_dir
    call("mkdir -p " + test_dir + " && "
         "cd " + test_dir + " && "
         "virtualenv venv0 && "
         "virtualenv venv1 && "
         "./venv0/bin/pip install pyyaml && "
         "./venv1/bin/pip install attrs",
         shell=True)
    return test_dir


def test_venv_identify_distributions(venv_test_dir):
    pydir = "python{v.major}.{v.minor}".format(v=sys.version_info)
    paths = ["lib/" + pydir + "/site-packages/yaml/parser.py",
             "lib/" + pydir + "/site-packages/attr/filters.py"]
    full_paths = [os.path.join(venv_test_dir, "venv{}".format(idx), f)
                  for idx, f in  enumerate(paths)]
    full_paths.append("/sbin/iptables")

    tracer = VenvTracer()

    dists = list(tracer.identify_distributions(full_paths))
    assert len(dists) == 1

    distributions, unknown_files = dists[0]
    assert unknown_files == ["/sbin/iptables"]

    assert len(distributions.environments) == 2

    expect = {"environments":
              [{"name": "venv0",
                "packages": [{"files": [paths[0]], "name": "PyYAML"}]},
               {"name": "venv1",
                "packages": [{"files": [paths[1]], "name": "attrs"}]}]}
    assert_is_subset_recur(expect, attr.asdict(distributions), [dict, list])
