# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from niceman.cmdline.main import main

import logging
import pprint
import os

from niceman.utils import swallow_logs
from niceman.tests.utils import assert_in

REPROZIP_SPEC_YML_FILENAME = os.path.join(os.path.dirname(__file__), os.pardir,
                                           os.pardir, 'tests', 'files',
                                           'reprozip_xeyes.yml')

def test_retrace():
    """
    Test installing packages on the localhost.
    """
    with swallow_logs(new_level=logging.DEBUG) as log:
        args = ['retrace',
                  '--spec', REPROZIP_SPEC_YML_FILENAME,
               ]
        main(args)
        assert_in("reading filename " + REPROZIP_SPEC_YML_FILENAME, log.lines)
