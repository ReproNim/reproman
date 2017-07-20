# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import pytest
from .constants import NICEMAN_SPEC1_YML_FILENAME, REPROZIP_SPEC2_YML_FILENAME

NICEMAN_SPECS = [
    NICEMAN_SPEC1_YML_FILENAME,
    # This one could have been another "serialization" of the effectively
    # identical spec on which we could try to run
    # REPROZIP_SPEC1
]

REPROZIP_SPEC2 = [
    REPROZIP_SPEC2_YML_FILENAME
]


# Let's make a convenience fixture to run tests against demo1 file(s)
@pytest.fixture(params=NICEMAN_SPECS)
def demo1_spec(request):
    yield request.param


@pytest.fixture(params=REPROZIP_SPEC2)
def reprozip_spec2(request):
    yield request.param

