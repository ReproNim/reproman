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

from niceman.utils import swallow_outputs
from niceman.tests.utils import assert_in, assert_not_in, assert_equal

files1_yaml = opj(dirname(__file__), 'files', 'files1.yaml')
files2_yaml = opj(dirname(__file__), 'files', 'files2.yaml')

def test_diff_files():
    with swallow_outputs() as outputs:
        args = ['diff', files1_yaml, files2_yaml]
        main(args)
        assert_in('Files:', outputs.out)
        assert_in('< /etc/a', outputs.out)
        assert_in('> /etc/c', outputs.out)
        assert_not_in('< /etc/b', outputs.out)
        assert_not_in('> /etc/b', outputs.out)
        assert_equal(outputs.err, '')
