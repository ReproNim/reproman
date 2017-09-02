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
    assert distributions[0].name == 'git'
    assert distributions[0].packages[0].files == [__file__]

    assert files == ['/nonexisting-for-sure']


@with_tempfile(mkdir=True)
def test_detached_git(repo=None):
    import os
    # XXX Replace with our session?
    from niceman.cmd import Runner
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    runner = Runner(env=env, cwd=repo)
    assert runner('git config user.name')[0], "git env should be set"
    assert runner('git config user.email')[0], "git env should be set"
    runner('git init')

    # should be good enough not to crash
    distributions, files = identify_distributions([repo])
    assert len(distributions) == 1
    dist = distributions[0]
    assert dist.name == 'git'
    packages = dist.packages
    assert len(packages) == 1
    pkg = packages[0]
    # we do not include repository path itself
    assert pkg.files == []
    assert pkg.path == repo

    # Let's now make it more sensible
    fname = opj(repo, "file")
    with open(fname, 'w') as f:
        f.write("data")
    runner("git add file")
    runner("git commit -m added file")
    distributions, files = identify_distributions([fname])
    assert len(distributions) == 1
    pkg = distributions[0].packages[0]
    assert pkg.files == [fname]
    hexsha = pkg.hexsha
    assert hexsha
    assert pkg.branch == 'master'

    # And if point to a directory under, should not identify the VCS
    # (since in principle git e.g. is not tracing directories)
    subdir = opj(repo, 'subdir')
    os.mkdir(subdir)
    distributions_, files_ = identify_distributions([subdir])
    assert distributions_ == []
    assert files_ == [subdir]

    # but if we point to a file under
    subfile = opj(subdir, 'file')
    with open(subfile, 'w') as f:
        pass
    runner("git add subdir/file")
    distributions__, files__ = identify_distributions([subfile])
    assert len(distributions__) == 1
    pkg = distributions__[0].packages[0]
    assert pkg.files == [subfile]

    # and if we cause a detachment
    runner("git rm file")
    runner("git commit -m removed file")
    runner("git checkout HEAD^", expect_stderr=True)
    distributions, files = identify_distributions([repo])
    pkg = distributions[0].packages[0]
    # we do not include repository path itself
    assert pkg.files == []
    assert pkg.hexsha == hexsha
    assert not pkg.branch
    assert not pkg.remotes
