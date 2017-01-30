# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import io
import pprint
import os

import niceman.retrace.rpzutil as rpzutil

import pytest
try:
    import apt
except Exception:
    apt = None

REPROZIP_SPEC_YML_FILENAME = os.path.join(os.path.dirname(__file__), os.pardir,
                                           os.pardir, 'tests', 'files',
                                           'reprozip_xeyes.yml')


@pytest.mark.skipif(not apt, reason="requires apt module")
def test_read_reprozip_yaml():
    config = rpzutil.read_reprozip_yaml(REPROZIP_SPEC_YML_FILENAME)
#    pprint.pprint(config)
    rpzutil.identify_packages(config)
    output = io.StringIO()
    rpzutil.write_config(output, config)
    assert True

