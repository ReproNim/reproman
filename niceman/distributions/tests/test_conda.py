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

import sys
from appdirs import AppDirs
from subprocess import call

import yaml
import attr
from niceman.formats.niceman import NicemanProvenance
from niceman.tests.utils import skip_if_no_network

try:
    import apt
except ImportError:
    apt = None

import json

from niceman.distributions.conda import CondaTracer


def create_test_conda(test_dir):
    if os.path.exists(test_dir):
        return
    call("mkdir -p " + test_dir + "; "
         "cd " + test_dir + "; "
         "curl -O https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh; "
         "bash -b Miniconda2-latest-Linux-x86_64.sh -b -p ./miniconda; "
         "./miniconda/bin/conda create -y -n mytest python=2.7;" + \
         "./miniconda/envs/mytest/bin/conda install -y xz -n mytest;" + \
         "./miniconda/envs/mytest/bin/pip install rpaths;",
         shell=True)


@skip_if_no_network
def test_conda_manager_identify_distributions():
    dirs = AppDirs('niceman')
    test_dir = os.path.join(dirs.user_cache_dir, 'conda_test')
    create_test_conda(test_dir)
    print (test_dir + "\n")
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
