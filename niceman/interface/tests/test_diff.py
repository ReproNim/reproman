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

multi_debian_yaml = opj(dirname(__file__), 'files', 'multi_debian.yaml')

def test_multi_debian_files():
    with swallow_logs() as log:
        args = ['diff', multi_debian_yaml, diff_1_yaml]
        with raises(SystemExit):
            main(args)
        assert_in_in('multiple Debian distributions found', log.lines)
    with swallow_logs() as log:
        args = ['diff', diff_1_yaml, multi_debian_yaml]
        with raises(SystemExit):
            main(args)
        assert_in_in('multiple Debian distributions found', log.lines)


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
