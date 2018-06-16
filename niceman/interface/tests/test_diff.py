# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import join as opj, dirname
from niceman.cmdline.main import main

from niceman.utils import swallow_outputs, swallow_logs
from niceman.tests.utils import assert_in, assert_not_in, assert_equal
from niceman.tests.utils import assert_in_in

from pytest import raises

diff_1_yaml = opj(dirname(__file__), 'files', 'diff_1.yaml')
diff_2_yaml = opj(dirname(__file__), 'files', 'diff_2.yaml')
empty_yaml = opj(dirname(__file__), 'files', 'empty.yaml')

multi_debian_yaml = opj(dirname(__file__), 'files', 'multi_debian.yaml')

def test_multi_debian_files():
    with swallow_logs() as log:
        args = ['diff', multi_debian_yaml, diff_1_yaml]
        with raises(SystemExit):
            main(args)
        assert_in_in("multiple <class 'niceman.distributions.debian.DebianDistribution'> found", log.lines)
    with swallow_logs() as log:
        args = ['diff', diff_1_yaml, multi_debian_yaml]
        with raises(SystemExit):
            main(args)
        assert_in_in("multiple <class 'niceman.distributions.debian.DebianDistribution'> found", log.lines)


def test_same():
    with swallow_outputs() as outputs:
        args = ['diff', diff_1_yaml, diff_1_yaml]
        main(args)
        assert_equal(outputs.out, '')
        assert_equal(outputs.err, '')


def test_diff_files():
    with swallow_outputs() as outputs:
        args = ['diff', diff_1_yaml, diff_2_yaml]
        main(args)
        assert_equal(outputs.err, '')
        assert_in('Files:', outputs.out)
        assert_in('< /etc/a', outputs.out)
        assert_in('> /etc/c', outputs.out)
        assert_not_in('< /etc/b', outputs.out)
        assert_not_in('> /etc/b', outputs.out)


def test_diff_debian_packages():
    with swallow_outputs() as outputs:
        args = ['diff', diff_1_yaml, diff_2_yaml]
        main(args)
        assert_equal(outputs.err, '')
        assert_in('Debian packages:', outputs.out)
        assert_in('< lib1only x86 2:1.6.4-3', outputs.out)
        assert_in('> lib2only x86 2:1.6.4-3', outputs.out)
        assert_in('< libarchdiff x86 2.4.6', outputs.out)
        assert_in('> libarchdiff amd64 2.4.6', outputs.out)
        assert_in('Debian package libversdiff x86:', outputs.out)
        assert_in('< 2.4.6', outputs.out)
        assert_in('> 2.4.7', outputs.out)
        assert_not_in('libsame', outputs.out)


def test_diff_conda_packages():
    with swallow_outputs() as outputs:
        args = ['diff', diff_1_yaml, diff_2_yaml]
        main(args)
        assert_equal(outputs.err, '')
        assert_in('Conda packages:', outputs.out)
        assert_in('< c_lib1only py36_0 2:1.6.4-3', outputs.out)
        assert_in('> c_lib2only py36_0 2:1.6.4-3', outputs.out)
        assert_in('< c_libbuilddiff py36_0 2.4.6', outputs.out)
        assert_in('> c_libbuilddiff hdf63c60_3 2.4.6', outputs.out)
        # TO DO: ensure the version strings (second and third lines below) 
        # come from the conda report -- these could just match the debian 
        # output checked in test_diff_debian_packages()
        assert_in('Conda package c_libversdiff py36_0:', outputs.out)
        assert_in('< 2.4.6', outputs.out)
        assert_in('> 2.4.7', outputs.out)
        assert_not_in('c_libsame', outputs.out)


def test_diff_no_distributions():
    with swallow_outputs() as outputs:
        args = ['diff', diff_1_yaml, empty_yaml]
        main(args)
        assert_equal(outputs.err, '')
        assert_in('Debian packages:', outputs.out)
        assert_in('< lib1only x86 2:1.6.4-3', outputs.out)
        assert_in('< libsame x86 2.4.6', outputs.out)
        assert_in('< libarchdiff x86 2.4.6', outputs.out)
        assert_in('< libversdiff x86 2.4.6', outputs.out)
        assert_in('Conda packages:', outputs.out)
        assert_in('< c_lib1only py36_0 2:1.6.4-3', outputs.out)
        assert_in('< c_libsame py36_0 2.4.6', outputs.out)
        assert_in('< c_libbuilddiff py36_0 2.4.6', outputs.out)
        assert_in('< c_libversdiff py36_0 2.4.6', outputs.out)
        assert_in('Files:', outputs.out)
        assert_in('< /etc/a', outputs.out)
        assert_in('< /etc/b', outputs.out)


def test_diff_git():
    with swallow_outputs() as outputs:
        args = ['diff', diff_1_yaml, diff_2_yaml]
        main(args)
        assert_equal(outputs.err, '')
        assert_in('Git repositories:', outputs.out)
        assert_in('< 43e8e6577c7bf493ddb01ea7d49bef7dc7a6643b (/path/to/git/repo/1/only)', outputs.out)
        assert_in('> 64b1865267891fdd1a45251ca6f32df213dc546e (/path/to/git/repo/2/only)', outputs.out)
        assert_in('Git repository 5b8267181f6cae8dc37aeef21ea54171bd932522', outputs.out)
        assert_in('< 3e3aaa73a9c0ca061c7679af5fa7318e70f528ac (/path/1/to/different/git/commit)', outputs.out)
        assert_in('> 9d199f7fa7e6f691719e0860c5cf81193e815ad5 (/path/2/to/different/git/commit)', outputs.out)
        assert_not_in('/path/1/to/common/git/repo', outputs.out)
        assert_not_in('/path/2/to/common/git/repo', outputs.out)
        assert_not_in('99ac7f69a070077038a9eb9eca61c028db97181d', outputs.out)
        assert_not_in('d057b128759d80a47500adba0c4d3e95092bb87f', outputs.out)


def test_diff_svn():
    with swallow_outputs() as outputs:
        args = ['diff', diff_1_yaml, diff_2_yaml]
        main(args)
        assert_equal(outputs.err, '')
        assert_in('SVN repositories:', outputs.out)
        assert_in('< c8ed47ab-45c9-818d-5d62-549dcc6d97d4 (/path/to/svn/repo/1/only)', outputs.out)
        assert_in('> d7192e3a-60de-5caa-ccdc9525dea75aabf (/path/to/svn/repo/2/only)', outputs.out)
        assert_in('SVN repository 95e4b738-84c7-154c-f082-34d40e21fdd4', outputs.out)
        assert_in('< 12 (/path/1/to/different/svn/commit)', outputs.out)
        assert_in('> 14 (/path/2/to/different/svn/commit)', outputs.out)
        assert_not_in('/path/1/to/common/svn/repo', outputs.out)
        assert_not_in('/path/2/to/common/svn/repo', outputs.out)
