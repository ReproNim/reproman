# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
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
from niceman.retrace.packagemanagers import DebTracer
from niceman.tests.utils import skip_if
from niceman.tests.utils import with_tempfile


def test_identify_packages():
    files = ["/usr/share/doc/xterm/copyright",
             "/usr/games/alienblaster",
             "/usr/share/icons/hicolor/48x48/apps/xterm-color.png",
             "/usr/share/doc/zlib1g/copyright",
             "/usr/bin/vim.basic",
             "/usr/share/bug/vim/script",
             "/home/butch"]
    # TODO: Mock I/O and detect correct analysis
    packages, origins, files = identify_packages(files)
    pprint(files)
    pprint(origins)
    pprint(packages)
    assert True


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
        assert DebTracer._find_release_file(
            fp('s_d_d_data_non-free_binary-amd64_Packages')) == \
               fp('s_d_d_data_InRelease')
        assert DebTracer._find_release_file(
            fp('s_d_d_data_non-free_binary-i386_Packages')) == \
               fp('s_d_d_data_InRelease')
        assert DebTracer._find_release_file(
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
