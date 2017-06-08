# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import join as opj, pardir, dirname
from os.path import lexists
from pprint import pprint

from ..retrace import identify_distributions

from niceman.tests.utils import skip_if
from niceman.tests.utils import with_tempfile


# TODO: mock it up or run only when under Debian
def test_identify_packages():
    files = ["/usr/share/doc/xterm/copyright",
             "/usr/games/alienblaster",
             "/usr/share/icons/hicolor/48x48/apps/xterm-color.png",
             "/usr/share/doc/zlib1g/copyright",
             "/usr/bin/vim.basic",
             "/usr/share/bug/vim/script",
             "/home/butch"]
    # Simple sanity check that the pipeline works
    distributions, files = identify_distributions(files)
    pprint(files)
    pprint(distributions)
    assert True


@skip_if(not lexists(opj(dirname(__file__), pardir, pardir, pardir, '.git')))
def test_identify_myself():
    distributions, files = identify_distributions([__file__, '/nonexisting-for-sure'])
    assert len(distributions) == 1
    assert distributions[0].type == 'git'
    assert distributions[0].files == [__file__]

    assert files == ['/nonexisting-for-sure']


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
    packages, files = identify_distributions([repo])
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg.files == [repo]
    assert pkg.type == 'git'

    # Let's now make it more sensible
    fname = opj(repo, "file")
    with open(fname, 'w') as f:
        f.write("data")
    runner("git add file")
    runner("git commit -m added file")
    packages, files = identify_distributions([fname])
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg.files == [fname]
    assert pkg.type == 'git'
    hexsha = pkg.hexsha
    assert hexsha
    assert pkg.branch == 'master'
    # and no field with None
    for v in pkg.values():
        assert v is not None

    # and if we cause a detachment
    runner("git rm file")
    runner("git commit -m removed file")
    runner("git checkout HEAD^")
    packages, files = identify_distributions([repo])
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg.files == [repo]
    assert pkg.type == 'git'
    assert pkg.hexsha == hexsha
    assert 'branch' not in pkg
