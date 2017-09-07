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
from subprocess import call

import yaml
import attr
from niceman.formats.niceman import NicemanProvenance

try:
    import apt
except ImportError:
    apt = None

import json

from niceman.distributions.conda import CondaTracer


def create_test_conda():
    if os.path.exists("/tmp/niceman_conda_test"):
        return
    call("mkdir /tmp/niceman_conda_test; "
         "cd /tmp/niceman_conda_test; "
         "curl -O https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh; "
         "bash -b Miniconda2-latest-Linux-x86_64.sh -b -p /tmp/niceman_conda_test/miniconda; "
         "/tmp/niceman_conda_test/miniconda/bin/conda create -y -n mytest python=2.7;"
         "/tmp/niceman_conda_test/miniconda/envs/mytest/bin/conda install -y xz -n mytest;"
         "/tmp/niceman_conda_test/miniconda/envs/mytest/bin/pip install pluggy;",
         shell=True)


def test_conda_manager_identify_distributions():
    create_test_conda()
    files = ["/tmp/niceman_conda_test/miniconda/bin/sqlite3",
             "/tmp/niceman_conda_test/miniconda/envs/mytest/bin/xz",
             "/tmp/niceman_conda_test/miniconda/envs/mytest/lib/python2.7/site-packages/pip/index.py",
             "/tmp/niceman_conda_test/miniconda/envs/mytest/lib/python2.7/site-packages/pluggy.py",
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
