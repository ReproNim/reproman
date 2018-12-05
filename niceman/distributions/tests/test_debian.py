# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import json
import os
from os.path import islink
from os.path import join, isfile

import logging

import attr

from niceman.distributions.debian import DebTracer
from niceman.distributions.debian import DEBPackage
from niceman.distributions.debian import DebianDistribution

import pytest

import mock

from niceman.utils import swallow_logs
from niceman.tests.utils import skip_if_no_apt_cache


@skip_if_no_apt_cache
def test_dpkg_manager_identify_packages():
    files = ["/sbin/iptables"]
    tracer = DebTracer()
    (packages, unknown_files) = \
        tracer.identify_packages_from_files(files)
    # Make sure that iptables was identified
    assert (not unknown_files), "/sbin/iptables should be identified"
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg.name == 'iptables'
    # Make sure apt_sources are identified, but then we should ask the entire
    # distribution
    distributions = list(tracer.identify_distributions(files))
    assert len(distributions) == 1
    distribution, unknown_files = distributions[0]
    assert distribution.apt_sources
    # Make sure both a non-local origin was found
    for o in distribution.apt_sources:
        if o.site:
            # Loop over mandatory attributes
            for a in ["name", "component", "origin",
                      "label", "site", "archive_uri"]:
                assert getattr(o, a), "A non-local origin needs a " + a
            # Note: date and architecture are not mandatory (and not found on
            # travis)
            break
    else:
        assert False, "A non-local origin must be found"


@pytest.mark.integration
@skip_if_no_apt_cache
def test_check_bin_packages():
    # Gather files in /usr/bin and /usr/lib
    files = list_all_files("/usr/bin") + list_all_files("/usr/lib")
    tracer = DebTracer()
    distributions = list(tracer.identify_distributions(files))
    assert len(distributions) == 1
    distribution, unknown_files = distributions[0]
    non_local_origins = [o for o in distribution.apt_sources if o.site]
    assert len(non_local_origins) > 0, "A non-local origin must be found"
    for o in non_local_origins:
        # Loop over mandatory attributes
        for a in ["name", "component", "origin",
                  "label", "site", "archive_uri"]:
            assert getattr(o, a), "A non-local origin needs a " + a
# Allow bin files to be not associated with a specific package
#    assert len(unknown_files) == 0, "Files not found in packages: " + \
#                                    str(unknown_files)


def list_all_files(dir):
    files = [join(dir, f) for f in os.listdir(dir)
             if (isfile(join(dir, f)) and
                 not islink(join(dir, f)))]
    return files


# def test_find_release_file():
#     fp = lambda p: os.path.join('/var/lib/apt/lists', p)
#
#     def mocked_exists(path):
#         return path in {
#             fp('s_d_d_data_crap_InRelease'),
#             fp('s_d_d_datas_InRelease'),
#             fp('s_d_d_data_InRelease'),
#             fp('s_d_d_sid_InRelease'),
#             fp('s_d_d_InRelease')
#         }
#
#     with mock.patch('os.path.exists', mocked_exists):
#         assert DebTracer._find_release_file(
#             fp('s_d_d_data_non-free_binary-amd64_Packages')) == \
#                fp('s_d_d_data_InRelease')
#         assert DebTracer._find_release_file(
#             fp('s_d_d_data_non-free_binary-i386_Packages')) == \
#                fp('s_d_d_data_InRelease')
#         assert DebTracer._find_release_file(
#             fp('oths_d_d_data_non-free_binary-i386_Packages')) is None


def test_trace_nonexisting_file():
    files = ["/is/not/there/"]
    manager = DebTracer()
    packages, unknown_files = manager.identify_packages_from_files(files)
    # get_details_for_packages doesn't fail on an empty package list.
    assert not packages
    packages = manager.get_details_for_packages(packages)
    assert not packages


def test_utf8_file():
    files = [u"/usr/share/ca-certificates/mozilla/"
             u"TÜBİTAK_UEKAE_Kök_Sertifika_Hizmet_Sağlayıcısı_-_Sürüm_3.crt"]
    manager = DebTracer()
    # Simple sanity check that the pipeline works with utf-8
    (packages, unknown_files) = \
        manager.identify_packages_from_files(files)
    packages = manager.get_details_for_packages(packages)
    # If the file exists, it should be in ca-certificates
    if os.path.isfile(files[0]):
        assert packages[0].name == "ca-certificates"
    else:  # Otherwise just make sure we didn't throw an exception
        assert True


def test_get_packagefields_for_files():
    manager = DebTracer()
    # TODO: mock! and bring back afni and fail2ban
    files = ['/bin/sh',  # the tricky one with alternatives etc, on my system - provided by dash
             '/lib/i386-linux-gnu/libz.so.1.2.8', '/lib/x86_64-linux-gnu/libz.so.1.2.8',  # multiarch
             '/usr/lib/afni/bin/afni',  # from contrib
             '/usr/bin/fail2ban-server', '/usr/bin/fail2ban-server', # arch all and multiple
             '/bogus'
             ]

    def exec_cmd_batch_mock(session, cmd, subfiles, exc_classes):
        assert subfiles == files  # we get all of the passed in
        assert cmd == ['dpkg-query', '-S']

        yield ("""\
diversion by dash from: /bin/sh
diversion by dash to: /bin/sh.distrib
dash: /bin/sh
zlib1g:i386: /lib/i386-linux-gnu/libz.so.1.2.8
zlib1g:amd64: /lib/x86_64-linux-gnu/libz.so.1.2.8
afni: /usr/lib/afni/bin/afni
fail2ban: /usr/bin/fail2ban-server
fail2ban: /usr/bin/fail2ban-server
""", None, None)
    with mock.patch('niceman.distributions.debian.execute_command_batch',
                    exec_cmd_batch_mock):
        out = manager._get_packagefields_for_files(files)

    assert out == {
        '/lib/i386-linux-gnu/libz.so.1.2.8': {'name': u'zlib1g', 'architecture': u'i386'},
        '/lib/x86_64-linux-gnu/libz.so.1.2.8': {'name': u'zlib1g', 'architecture': u'amd64'},
        '/usr/bin/fail2ban-server': {'name': u'fail2ban'},
        '/usr/lib/afni/bin/afni': {'name': u'afni'},
        '/bin/sh': {'name': u'dash'}
    }


def test_parse_dpkgquery_line():
    parse = DebTracer()._parse_dpkgquery_line

    mock_values = {
        "unique": {"name": "pkg",
                   "path": "/path/to/file",
                   "pkgs_rest": None},
        "multi_dir": {"name": "pkg",
                      "path": os.getcwd(),
                      "pkgs_rest": ", more, packages"},
        "multi_file": {"name": "pkg",
                       "path": __file__,
                       "pkgs_rest": ", more, packages"}
    }

    with mock.patch("niceman.distributions.debian.parse_dpkgquery_line",
                    mock_values.get):
        assert parse("unique") == {"name": "pkg",
                                   "path": "/path/to/file"}
        assert parse("multi_dir") is None
        with swallow_logs(new_level=logging.WARNING) as log:
            assert parse("multi_file") == {"name": "pkg",
                                           "path": __file__}
            assert any("multiple packages " in ln for ln in log.lines)


@pytest.fixture
def setup_packages():
    """set up the package comparison tests"""
    a = DEBPackage(name='p1')
    b = DEBPackage(name='p1', version='1.0')
    c = DEBPackage(name='p1', version='1.1')
    d = DEBPackage(name='p1', architecture='i386')
    e = DEBPackage(name='p1', architecture='alpha')
    f = DEBPackage(name='p1', version='1.1', architecture='i386')
    g = DEBPackage(name='p2')
    return (a, b, c, d, e, f, g)

def test_package_satisfies(setup_packages):
    (p1, p1v10, p1v11, p1ai, p1aa, p1v11ai, p2) = setup_packages
    assert p1.satisfies(p1)
    assert p1v10.satisfies(p1v10)
    assert not p1.satisfies(p1v10)
    assert p1v10.satisfies(p1)
    assert not p1v10.satisfies(p1v11)
    assert not p1.satisfies(p2)
    assert not p1v10.satisfies(p2)
    assert not p2.satisfies(p1v10)
    assert not p1v10.satisfies(p1aa)
    assert p1aa.satisfies(p1)
    assert not p1aa.satisfies(p1v10)
    assert not p1aa.satisfies(p1ai)
    assert not p1v11.satisfies(p1v11ai)
    assert p1v11ai.satisfies(p1v11)

@pytest.fixture
def setup_distributions(setup_packages):
    (p1, p1v10, p1v11, p1ai, p1aa, p1v11ai, p2) = setup_packages
    d1 = DebianDistribution(name='debian 1')
    d1.packages = [p1]
    d2 = DebianDistribution(name='debian 2')
    d2.packages = [p1v11]
    return (d1, d2)

def test_distribution_satisfies_package(setup_distributions, setup_packages):
    (d1, d2) = setup_distributions
    (p1, p1v10, p1v11, p1ai, p1aa, p1v11ai, p2) = setup_packages
    assert d1.satisfies_package(p1)
    assert not d1.satisfies_package(p1v10)
    assert d2.satisfies_package(p1)
    assert not d2.satisfies_package(p1v10)
    assert d2.satisfies_package(p1v11)

def test_distribution_statisfies(setup_distributions):
    (d1, d2) = setup_distributions
    assert not d1.satisfies(d2)
    assert d2.satisfies(d1)

def test_distribution_sub(setup_packages):
    (p1, p1v10, p1v11, p1ai, p1aa, p1v11ai, p2) = setup_packages
    d1 = DebianDistribution(name='debian 1')
    d1.packages = [p1, p2]
    d2 = DebianDistribution(name='debian 2')
    d2.packages = [p1v11, p2]
    assert d1-d2 == []
    result = d2-d1
    assert len(result) == 1
    assert result[0] == p1v11
