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

from niceman.utils import swallow_logs
from niceman.tests.utils import assert_in

def test_retrace(reprozip_spec2):
    """
    Test installing packages on the localhost.
    """
    with swallow_logs(new_level=logging.DEBUG) as log:
        args = ['retrace',
                '--spec', reprozip_spec2,
                ]
        main(args)
        assert_in("reading filename " + reprozip_spec2, log.lines)
