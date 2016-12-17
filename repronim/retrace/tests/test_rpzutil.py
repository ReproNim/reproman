# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import pprint

import repronim.retrace.rpzutil as rpzutil
from repronim.tests.test_constants import REPROZIP_SPEC1_YML_FILENAME


def test_read_reprozip_yaml():
    config = rpzutil.read_reprozip_yaml(REPROZIP_SPEC1_YML_FILENAME)
    pprint.pprint(config)
    assert True
