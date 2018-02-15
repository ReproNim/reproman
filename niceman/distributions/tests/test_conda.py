# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import collections
import io
import logging
import os
import pytest

import sys
from appdirs import AppDirs
from mock import mock
from subprocess import call
from unittest import SkipTest

import yaml
import attr

from niceman.formats.niceman import NicemanProvenance
from niceman.tests.utils import skip_if_no_network, assert_is_subset_recur

import json

from niceman.distributions.conda import CondaTracer, CondaDistribution, \
    CondaEnvironment, CondaPackage, CondaChannel


@pytest.fixture(scope="session")
@skip_if_no_network
def get_conda_test_dir():
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
    test_dir = get_conda_test_dir
    files = [os.path.join(test_dir, "miniconda/bin/sqlite3"),
             os.path.join(test_dir, "miniconda/envs/mytest/bin/xz"),
             os.path.join(test_dir, "miniconda/envs/mytest/lib/python2.7/site-packages/pip/index.py"),
             os.path.join(test_dir, "miniconda/envs/mytest/lib/python2.7/site-packages/rpaths.py"),
             "/sbin/iptables"]
    tracer = CondaTracer()
    dists = list(tracer.identify_distributions(files))

    assert len(dists) == 1, "Exactly one Conda distribution expected."

    (distributions, unknown_files) = dists[0]

    assert unknown_files == ["/sbin/iptables"], \
        "Exactly one file (/sbin/iptables) should not be discovered."

    assert len(distributions.environments) == 2, \
        "Two conda environments are expected."

    out = {'environments': [{'packages': [{'files': ['bin/sqlite3'],
                                           'name': 'sqlite'}]},
                            {'packages': [{'files': ['bin/xz'],
                                           'name': 'xz'},
                                          {'files': ['lib/python2.7/site-packages/pip/index.py'],
                                           'name': 'pip'},
                                          {'files': ['lib/python2.7/site-packages/rpaths.py'],
                                           'installer': 'pip',
                                           'name': 'rpaths'}
                                          ]
                             }
                            ]
           }
    assert_is_subset_recur(out, attr.asdict(distributions), [dict, list])
    # NicemanProvenance.write(sys.stdout, distributions)
    # print(json.dumps(unknown_files, indent=4))


def test_format_conda_package():
    assert "p" == CondaDistribution.format_conda_package("p")
    assert "p=v" == CondaDistribution.format_conda_package("p", "v")
    assert "p=v=b" == CondaDistribution.format_conda_package("p", "v", "b")
    assert "p" == CondaDistribution.format_conda_package("p", None, "b")


def test_format_pip_package():
    assert "p" == CondaDistribution.format_pip_package("p")
    assert "p==v" == CondaDistribution.format_pip_package("p", "v")


def test_create_conda_export():
    env = CondaEnvironment(
        name="conda_env-1",
        path="/home/butch/.cache/niceman/conda_test/miniconda/envs/mytest",
        conda_version="4.3.31",
        python_version="3.6.3.final.0",
        packages=[{
            "name": "xz",
            "installer": None,
            "version": "5.2.3",
            "build": "0",
            "channel_name": "conda-forge",
            "md5": "f4e0d30b3caf631be7973cba1cf6f601",
            "size": "874292",
            "url": "https://conda.anaconda.org/conda-forge/linux-64/xz-5.2.3-0.tar.bz2",
            "files": ["bin/xz", ],
        }, {
            "name": "rpaths",
            "installer": "pip",
            "version": "0.13",
            "build": None,
            "channel_name": None,
            "md5": None,
            "size": None,
            "url": None,
            "files": ["lib/python2.7/site-packages/rpaths.py", ],
        }, ],
        channels=[{
            "name": "conda-forge",
            "url": "https://conda.anaconda.org/conda-forge/linux-64",
        }, ],
    )
    out = {"name": "mytest",
           "channels": ["conda-forge"],
           "dependencies": ["xz=5.2.3=0",
                            {"pip": ["rpaths==0.13"]}],
           "prefix": "/home/butch/.cache/niceman/conda_test/miniconda/envs/mytest"
           }
    export = yaml.safe_load(CondaDistribution.create_conda_export(env))
    assert export == out


@skip_if_no_network
def test_conda_init_and_install():
    # TODO: Make situations where is fails
    # TODO: Make a marker as an "integration test" (and mark the debian /usr/bin detection test)
    dist = CondaDistribution(
        name="conda",
        path="/tmp/niceman_conda/miniconda",
        conda_version="4.3.31",
        python_version="2.7.14.final.0",
        environments=[
            CondaEnvironment(
                name="root",
                path="/tmp/niceman_conda/miniconda",
                conda_version="4.3.31",
                python_version="2.7.14.final.0",
                packages=[{
                    "name": "pip",
                    "installer": None,
                    "version": "9.0.1",
                    "build": None,
                    "channel_name": None,
                    "md5": None,
                    "size": None,
                    "url": None,
                    "files": None,
                }, {
                    "name": "pytest",
                    "installer": "pip",
                    "version": "3.4.0",
                    "build": None,
                    "channel_name": None,
                    "md5": None,
                    "size": None,
                    "url": None,
                    "files": None,
                }, ],
                channels=[{
                    "name": "conda-forge",
                    "url": "https://conda.anaconda.org/conda-forge/linux-64",
                }, {
                    "name": "defaults",
                    "url": "https://repo.continuum.io/pkgs/main/linux-64",
                }, ],
            ),
            CondaEnvironment(
                name="mytest",
                path="/tmp/niceman_conda/miniconda/envs/mytest",
                conda_version="4.3.31",
                python_version="3.6.3.final.0",
                packages=[{
                    "name": "pip",
                    "installer": None,
                    "version": "9.0.1",
                    "build": None,
                    "channel_name": None,
                    "md5": None,
                    "size": None,
                    "url": None,
                    "files": None,
                }, {
                    "name": "xz",
                    "installer": None,
                    "version": "5.2.3",
                    "build": "0",
                    "channel_name": "conda-forge",
                    "md5": "f4e0d30b3caf631be7973cba1cf6f601",
                    "size": "874292",
                    "url": "https://conda.anaconda.org/conda-forge/linux-64/xz-5.2.3-0.tar.bz2",
                    "files": ["bin/xz", ],
                }, {
                    "name": "rpaths",
                    "installer": "pip",
                    "version": "0.13",
                    "build": None,
                    "channel_name": None,
                    "md5": None,
                    "size": None,
                    "url": None,
                    "files": ["lib/python2.7/site-packages/rpaths.py", ],
                }, ],
                channels=[{
                    "name": "conda-forge",
                    "url": "https://conda.anaconda.org/conda-forge/linux-64",
                }, ],
            ),
        ])
    dist.initiate(None)
    dist.install_packages()
    # TODO: Verify installation!
    # TODO: Mock instead of real execution


def test_parse_conda_export_pip_package_entry():
    assert CondaTracer.parse_pip_package_entry("appdirs==1.4.3") == (
        "appdirs", None)
    assert CondaTracer.parse_pip_package_entry(
        "niceman (/test/repronim)==0.0.2") == (
           "niceman", "/test/repronim")


def test_get_conda_env_export_exceptions():
    # Mock to capture logs
    def log_warning(msg, *args):
        log_warning.val = msg % args if args else msg

    # Mock to throw unrecognized argument exception
    def raise_unrec_args(_):
        raise Exception("conda-env: error: unrecognized arguments: -p"
                        "/home/butch/old_conda/")

    # Mock to raise some other exception
    def raise_other(_):
        raise Exception("unknown")

    from niceman.distributions.conda import lgr

    tracer = CondaTracer()
    with mock.patch.object(tracer._session, "execute_command",
                           raise_unrec_args), \
         mock.patch.object(lgr, "warning", log_warning):
        tracer._get_conda_env_export("", "/conda")
        assert "Please use Conda 4.3.19" in log_warning.val

    with mock.patch.object(tracer._session, "execute_command",
                           raise_other), \
        mock.patch.object(lgr, "warning", log_warning):
        tracer._get_conda_env_export("", "/conda")
        assert "unknown" in log_warning.val

