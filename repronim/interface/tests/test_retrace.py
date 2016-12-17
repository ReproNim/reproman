# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.cmdline.main import main

import logging
import pprint

from repronim.tests.test_constants import REPROZIP_SPEC1_YML_FILENAME
from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in

def test_retrace():
    """
    Test installing packages on the localhost.
    """
    with swallow_logs(new_level=logging.DEBUG) as log:
        args = ['retrace',
                  '--spec', REPROZIP_SPEC1_YML_FILENAME,
               ]
        main(args)
        assert_in("reading filename " + REPROZIP_SPEC1_YML_FILENAME, log.lines)
