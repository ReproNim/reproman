# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import pytest
from .constants import DEMO_SPEC1_YML_FILENAME, REPRONIM_CFG_PATH

DEMO1_SPECS = [
    DEMO_SPEC1_YML_FILENAME,
    # This one could have been another "serialization" of the effectively
    # identical spec on which we could try to run
    # REPROZIP_SPEC1
]

# Substitutes in for user's ~/.config/repronim.cfg file
CONFIGURATION = [
    REPRONIM_CFG_PATH
]


# Let's make a convenience fixture to run tests against demo1 file(s)
@pytest.fixture(params=DEMO1_SPECS)
def demo1_spec(request):
    yield request.param


@pytest.fixture(params=CONFIGURATION)
def repronim_cfg_path(request):
    yield request.param

