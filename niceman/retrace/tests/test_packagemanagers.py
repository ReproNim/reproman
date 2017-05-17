# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# -*- coding: utf-8 -*-
#  ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os
import mock

from pprint import pprint
from os.path import lexists
from os.path import join as opj, pardir, dirname

from niceman.retrace.packagemanagers import identify_packages
from niceman.retrace.packagemanagers import DpkgManager
from niceman.tests.utils import skip_if
from niceman.tests.utils import with_tempfile

try:
    import apt
except ImportError:
    apt = None


def test_identify_packages():
    files = ["/usr/share/doc/xterm/copyright",
             "/usr/games/alienblaster",
             "/usr/share/icons/hicolor/48x48/apps/xterm-color.png",
             "/usr/share/doc/zlib1g/copyright",
             "/usr/bin/vim.basic",
             "/usr/share/bug/vim/script",
             "/home/butch"]
    # Simple sanity check that the pipeline works
    packages, origins, files = identify_packages(files)
    pprint(files)
    pprint(origins)
    pprint(packages)
    assert True


@skip_if(not apt)
def test_utf8_file():
    files = [u"/usr/share/ca-certificates/mozilla/TÜBİTAK_UEKAE_Kök_Sertifika_Hizmet_Sağlayıcısı_-_Sürüm_3.crt"]
    # Simple sanity check that the pipeline works with utf-8
    packages, origins, files = identify_packages(files)
    pprint(files)
    pprint(origins)
    pprint(packages)
    assert True


@skip_if(not apt)
def test_dpkg_manager_identify_packages():
    files = ["/sbin/iptables"]
    manager = DpkgManager()
    (packages, unknown_files) = \
        manager.search_for_files(files)
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


@skip_if(not lexists(opj(dirname(__file__), pardir, pardir, pardir, '.git')))
def test_identify_myself():
    packages, origins, files = identify_packages([__file__, '/nonexisting-for-sure'])
    assert len(packages) == 1
    assert packages[0]['type'] == 'git'
    assert packages[0]['files'] == [__file__]

    assert files == ['/nonexisting-for-sure']


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
        assert DpkgManager._find_release_file(
            fp('s_d_d_data_non-free_binary-amd64_Packages')) == \
                fp('s_d_d_data_InRelease')
        assert DpkgManager._find_release_file(
            fp('s_d_d_data_non-free_binary-i386_Packages')) == \
                fp('s_d_d_data_InRelease')
        assert DpkgManager._find_release_file(
            fp('oths_d_d_data_non-free_binary-i386_Packages')) is None


@with_tempfile(mkdir=True)
def test_detached_git(repo=None):
    import os
    from niceman.cmd import Runner
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    runner = Runner(env=env, cwd=repo)
    assert runner('git config user.name')[0], "git env should be set"
    assert runner('git config user.email')[0], "git env should be set"
    runner('git init')

    # should be good enough not to crash
    packages, origins, files = identify_packages([repo])
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg['files'] == [repo]
    assert pkg['type'] == 'git'

    # Let's now make it more sensible
    fname = opj(repo, "file")
    with open(fname, 'w') as f:
        f.write("data")
    runner("git add file")
    runner("git commit -m added file")
    packages, origins, files = identify_packages([fname])
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg['files'] == [fname]
    assert pkg['type'] == 'git'
    hexsha = pkg['hexsha']
    assert hexsha
    assert pkg['branch'] == 'master'
    # and no field with None
    for v in pkg.values():
        assert v is not None

    # and if we cause a detachment
    runner("git rm file")
    runner("git commit -m removed file")
    runner("git checkout HEAD^")
    packages, origins, files = identify_packages([repo])
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg['files'] == [repo]
    assert pkg['type'] == 'git'
    assert pkg['hexsha'] == hexsha
    assert 'branch' not in pkg
