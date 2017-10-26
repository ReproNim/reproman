# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import collections
import os
import pytest

import sys
from appdirs import AppDirs
from subprocess import call
from unittest import SkipTest

import yaml
import attr
from niceman.formats.niceman import NicemanProvenance
from niceman.tests.utils import skip_if_no_network

import json

from niceman.distributions.conda import CondaTracer


@pytest.fixture
def get_conda_test_dir():
    # Return none if no network is avaialble
    if os.environ.get('NICEMAN_TESTS_NONETWORK'):
        return None
    dirs = AppDirs('niceman')
    test_dir = os.path.join(dirs.user_cache_dir, 'conda_test')
    if os.path.exists(test_dir):
        return test_dir
    # Miniconda isn't installed, so install it
    if sys.platform.startswith('darwin'):
        miniconda_sh = "Miniconda2-latest-MacOSX-x86_64.sh"
    elif sys.platform.startswith('linux'):
        miniconda_sh = "Miniconda2-latest-Linux-x86_64.sh"
    else:
        raise ValueError("Conda test not supported with platform %s " %
                         sys.platform)
    call("mkdir -p " + test_dir + "; "
         "cd " + test_dir + "; "
         "curl -O https://repo.continuum.io/miniconda/" + miniconda_sh + "; "
         "bash -b " + miniconda_sh + " -b -p ./miniconda; "
         "./miniconda/bin/conda create -y -n mytest python=2.7; "
         "./miniconda/envs/mytest/bin/conda install -y xz -n mytest; "
         "./miniconda/envs/mytest/bin/pip install rpaths;",
         shell=True)
    return test_dir


def test_conda_manager_identify_distributions(get_conda_test_dir):
    # Skip if network is not available (skip_if_no_network fails with fixtures)
    test_dir = get_conda_test_dir
    if not test_dir:
        raise SkipTest("Skipping since no network settings")
    files = [os.path.join(test_dir, "miniconda/bin/sqlite3"),
             os.path.join(test_dir, "miniconda/envs/mytest/bin/xz"),
             os.path.join(test_dir, "miniconda/envs/mytest/lib/python2.7/site-packages/pip/index.py"),
             os.path.join(test_dir, "miniconda/envs/mytest/lib/python2.7/site-packages/rpaths.py"),
             "/sbin/iptables"]
    tracer = CondaTracer()
    dists = list(tracer.identify_distributions(files))

    assert len(dists) == 1, "Exactly one Conda distribution expected."

    (distributions, unknown_files) = dists[0]

    assert (len(unknown_files) == 1) and \
           (unknown_files[0] == "/sbin/iptables"), \
        "Exactly one file (/sbin/iptables) should not be discovered."

    assert len(distributions.environments) == 2, \
        "Two conda environments are expected."

    NicemanProvenance.write(sys.stdout, distributions)
    print(json.dumps(unknown_files, indent=4))
