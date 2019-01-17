# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import os
import pytest

import sys
from mock import mock
from subprocess import call

import yaml
import attr

from niceman.formats.niceman import NicemanProvenance
from niceman.tests.utils import create_pymodule
from niceman.tests.utils import skip_if_no_network, assert_is_subset_recur

from niceman.distributions.conda import CondaTracer, CondaDistribution, \
    CondaEnvironment, CondaPackage, CondaChannel, \
    get_conda_platform_from_python, get_miniconda_url


def test_get_conda_platform_from_python():
    assert get_conda_platform_from_python("linux2") == "linux"
    assert get_conda_platform_from_python("darwin") == "osx"


def test_get_miniconda_url():
    assert get_miniconda_url("linux-64", "2.7") == \
           "https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh"
    assert get_miniconda_url("linux-32", "3.4") == \
           "https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86.sh"
    assert get_miniconda_url("osx-64", "3.5.1") == \
           "https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"


def test_get_simple_python_version():
    assert CondaDistribution.get_simple_python_version("2.7.12.final.0") == \
           "2.7.12"
    assert CondaDistribution.get_simple_python_version("3.5.1") == \
           "3.5.1"


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
        name="mytest",
        path="/home/butch/.cache/niceman/conda_test/miniconda/envs/mytest",
        packages=[
            CondaPackage(
                name="xz",
                installer=None,
                version="5.2.3",
                build="0",
                channel_name="conda-forge",
                md5="f4e0d30b3caf631be7973cba1cf6f601",
                size="874292",
                url="https://conda.anaconda.org/conda-forge/linux-64/xz-5.2.3-0.tar.bz2",
                files=["bin/xz"]),
            CondaPackage(
                name="rpaths",
                installer="pip",
                version="0.13",
                build=None,
                channel_name=None,
                md5=None,
                size=None,
                url=None,
                files=["lib/python2.7/site-packages/rpaths.py"])],
        channels=[
            CondaChannel(
                name="conda-forge",
                url="https://conda.anaconda.org/conda-forge/linux-64")])
    out = {"name": "mytest",
           "channels": ["conda-forge"],
           "dependencies": ["xz=5.2.3=0",
                            {"pip": ["rpaths==0.13"]}],
           "prefix": "/home/butch/.cache/niceman/conda_test/miniconda/envs/mytest"
           }
    export = yaml.safe_load(CondaDistribution.create_conda_export(env))
    assert export == out


@pytest.mark.integration
@skip_if_no_network
def test_conda_init_install_and_detect():
    test_dir = "/tmp/niceman_conda/miniconda"

    dist = CondaDistribution(
        name="conda",
        path=test_dir,
        conda_version="4.3.31",
        python_version="2.7.14.final.0",
        platform=get_conda_platform_from_python(sys.platform) + "-64",
        environments=[
            CondaEnvironment(
                name="root",
                path=test_dir,
                packages=[
                    CondaPackage(
                        name="conda",
                        installer=None,
                        version="4.3.31",
                        build=None,
                        channel_name=None,
                        md5=None,
                        size=None,
                        url=None,
                        files=None),
                    CondaPackage(
                        name="pip",
                        installer=None,
                        version="9.0.1",
                        build=None,
                        channel_name=None,
                        md5=None,
                        size=None,
                        url=None,
                        files=None),
                    CondaPackage(
                        name="pytest",
                        installer="pip",
                        version="3.4.0",
                        build=None,
                        channel_name=None,
                        md5=None,
                        size=None,
                        url=None,
                        files=None)],
                channels=[
                    CondaChannel(
                        name="conda-forge",
                        url="https://conda.anaconda.org/conda-forge/linux-64"),
                    CondaChannel(
                        name="defaults",
                        url="https://repo.continuum.io/pkgs/main/linux-64")]),
            CondaEnvironment(
                name="mytest",
                path=os.path.join(test_dir, "envs/mytest"),
                packages=[
                    CondaPackage(
                        name="pip",
                        installer=None,
                        version="9.0.1",
                        build=None,
                        channel_name=None,
                        md5=None,
                        size=None,
                        url=None,
                        files=None),
                    CondaPackage(
                        name="xz",
                        installer=None,
                        version="5.2.3",
                        build="0",
                        channel_name="conda-forge",
                        md5="f4e0d30b3caf631be7973cba1cf6f601",
                        size="874292",
                        url="https://conda.anaconda.org/conda-forge/linux-64/xz-5.2.3-0.tar.bz2",
                        files=["bin/xz", ]),
                    CondaPackage(
                        name="rpaths",
                        installer="pip",
                        version="0.13",
                        build=None,
                        channel_name=None,
                        md5=None,
                        size=None,
                        url=None,
                        files=["lib/python2.7/site-packages/rpaths.py"])],
                channels=[
                    CondaChannel(
                        name="conda-forge",
                        url="https://conda.anaconda.org/conda-forge/linux-64")])])
    # First install the environment in /tmp/niceman_conda/miniconda
    dist.initiate(None)
    dist.install_packages()
    # Add an empty environment to test detection of them
    if not os.path.exists(os.path.join(test_dir, "envs/empty")):
        call("cd " + test_dir + "; " +
             "./bin/conda create -y -n empty; ",
             shell=True)

    # Test that editable packages are detected
    pymod_dir = os.path.join(test_dir, "minimal_pymodule")
    if not os.path.exists(pymod_dir):
        create_pymodule(pymod_dir)
        call([os.path.join(test_dir, "envs/mytest/bin/pip"),
              "install", "-e", pymod_dir])

    # Now pick some files we know are in the conda install and detect them
    files = [os.path.join(test_dir, "bin/pip"),
             os.path.join(test_dir, "envs/mytest/bin/xz"),
             os.path.join(test_dir, "envs/empty/conda-meta/history"),
             ]
    tracer = CondaTracer()
    dists = list(tracer.identify_distributions(files))

    assert len(dists) == 1, "Exactly one Conda distribution expected."

    (distributions, unknown_files) = dists[0]

    # NicemanProvenance.write(sys.stdout, distributions)

    assert distributions.platform.startswith(
        get_conda_platform_from_python(sys.platform)), \
        "A conda platform is expected."

    assert len(distributions.environments) == 3, \
        "Three conda environments are expected."

    out = {'environments': [{'name': 'root',
                             'packages': [{'name': 'pip'}]},
                            {'name': 'mytest',
                             'packages': [{'name': 'xz'},
                                          {'name': 'pip'},
                                          {'name': 'rpaths',
                                           'installer': 'pip',
                                           'editable': False},
                                          {'name': 'nmtest',
                                           'files': [],
                                           'installer': 'pip',
                                           'editable': True}]
                             }
                            ]
           }
    assert_is_subset_recur(out, attr.asdict(distributions), [dict, list])

    # conda packages are not repeated as "pip" packages.
    for envs in distributions.environments:
        for pkg in envs.packages:
            if pkg.name == "pip":
                assert pkg.installer is None

    # Smoke test to make sure install_packages doesn't choke on the format that
    # is actually returned by the tracer.
    distributions.initiate(None)
    distributions.install_packages()


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

conda_yaml = os.path.join(os.path.dirname(__file__), 'files', 'conda.yaml')

def test_conda_packages():
    env = NicemanProvenance(conda_yaml).get_environment()
    conda_dist = env.get_distribution(CondaDistribution)
    assert isinstance(conda_dist.packages, list)
    assert len(conda_dist.packages) == 4
