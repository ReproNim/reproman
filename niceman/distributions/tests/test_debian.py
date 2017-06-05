# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os
try:
    import apt
except ImportError:
    apt = None

from pprint import pprint

from niceman.distributions.debian import DebTracer

import mock
from niceman.tests.utils import skip_if


@skip_if(not apt)
def test_dpkg_manager_identify_packages():
    files = ["/sbin/iptables"]
    manager = DebTracer()
    (packages, unknown_files) = \
        manager.identify_packages_from_files(files)
    origins = manager.identify_package_origins(packages)
    # Make sure that iptables was identified
    assert (not unknown_files), "/sbin/iptables should be identified"
    # Make sure an origin is found
    assert origins
    # Make sure both a non-local origin was found
    for o in origins:
        if o.site:
            assert o.name, "A non-local origin needs a name"
            assert o.component, "A non-local origin needs a component"
            assert o.archive, "A non-local origin needs a archive"
            assert o.codename, "A non-local origin needs a codename"
            assert o.origin, "A non-local origin needs an origin"
            assert o.label, "A non-local origin needs a label"
            assert o.site, "A non-local origin needs a site"
            assert o.archive_uri, "An archive_uri should have been found"
            assert o.date, "An package should have been found"
            # Note: architecture is not mandatory (and not found on travis)
            break
    else:
        assert False, "A non-local origin must be found"
    pprint(origins)
    pprint(packages)


def test_find_release_file():
    fp = lambda p: os.path.join('/var/lib/apt/lists', p)

    def mocked_exists(path):
        return path in {
            fp('s_d_d_data_crap_InRelease'),
            fp('s_d_d_datas_InRelease'),
            fp('s_d_d_data_InRelease'),
            fp('s_d_d_sid_InRelease'),
            fp('s_d_d_InRelease')
        }

    with mock.patch('os.path.exists', mocked_exists):
        assert DebTracer._find_release_file(
            fp('s_d_d_data_non-free_binary-amd64_Packages')) == \
               fp('s_d_d_data_InRelease')
        assert DebTracer._find_release_file(
            fp('s_d_d_data_non-free_binary-i386_Packages')) == \
               fp('s_d_d_data_InRelease')
        assert DebTracer._find_release_file(
            fp('oths_d_d_data_non-free_binary-i386_Packages')) is None


@skip_if(not apt)
def test_utf8_file():
    files = [u"/usr/share/ca-certificates/mozilla/"
             u"TÜBİTAK_UEKAE_Kök_Sertifika_Hizmet_Sağlayıcısı_-_Sürüm_3.crt"]
    manager = DebTracer()
    # Simple sanity check that the pipeline works with utf-8
    (packages, unknown_files) = \
        manager.identify_packages_from_files(files)
    # Print for manual debugging
    pprint(unknown_files)
    pprint(packages)
    # If the file exists, it should be in ca-certificates
    if os.path.isfile(files[0]):
        assert packages[0]["name"] == "ca-certificates"
    else:  # Otherwise just make sure we didn't throw an exception
        assert True


def test_parse_dpkgquery_line():
    parse = DebTracer._parse_dpkgquery_line
    assert parse('zlib1g:i386: /lib/i386-linux-gnu/libz.so.1.2.8') == \
        {'name': 'zlib1g', 'architecture': 'i386', 'path': '/lib/i386-linux-gnu/libz.so.1.2.8'}

    assert parse('fail2ban: /usr/bin/fail2ban-client') == \
           {'name': 'fail2ban', 'path': '/usr/bin/fail2ban-client'}

    assert parse('diversion by dash from: /bin/sh') is None


def test_get_packagefields_for_files():
    manager = DebTracer()
    # TODO: mock!
    out = manager._get_packagefields_for_files(
        ['/bin/sh',  # the tricky one with alternatives etc, on my system - provided by dash
         '/lib/i386-linux-gnu/libz.so.1.2.8', '/lib/x86_64-linux-gnu/libz.so.1.2.8',  # multiarch
         '/usr/lib/afni/bin/afni',  # from contrib
         '/usr/bin/fail2ban-server', '/usr/bin/fail2ban-server', # arch all and multiple
         '/bogus'
         ])
    assert out == {
        '/lib/i386-linux-gnu/libz.so.1.2.8': {'name': u'zlib1g', 'architecture': u'i386'},
        '/lib/x86_64-linux-gnu/libz.so.1.2.8': {'name': u'zlib1g', 'architecture': u'amd64'},
        '/usr/bin/fail2ban-server': {'name': u'fail2ban'},
        '/usr/lib/afni/bin/afni': {'name': u'afni'},
        '/bin/sh': {'name': u'dash'}
    }