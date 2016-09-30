# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.cmdline.main import main

import os
import logging
from os.path import dirname, abspath

from mock import patch, call

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_equal
from repronim.tests.utils import assert_in


def test_install_main():
    """
    Install two packages locally: base-files and bash
    """
    testfile = dirname(abspath(__file__)) + os.path.sep + 'sample_reprozip_output_small.yml'
    with patch('subprocess.call', return_value="installed smth") as mocked_call, \
        swallow_logs(new_level=logging.DEBUG) as cml:
        main(['install', '--spec', testfile, '--platform', 'localhost'])
        # mocked_call

        # TODO: figure out why this one didn't work
        #mocked_call.assert_has_calls(
        assert_equal(
            [
                call(['sudo', 'apt-get', 'install', '-y', f])
                for f in ('base-files', 'bash')
            ],
            mocked_call.call_args_list
        )
        assert_in("Installing package: base-files", cml.out)
        assert_in("installed smth", cml.out)


        #import pdb; pdb.set_trace()
        #mocked_call.assert_has_calls()
        #assert_called_once_with(['sudo', 'apt-get', 'install'])


