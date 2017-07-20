# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import pytest
from .constants import NICEMAN_CFG_PATH

# Substitutes in for user's ~/.config/niceman.cfg file
CONFIGURATION = [
    NICEMAN_CFG_PATH
]

@pytest.fixture(params=CONFIGURATION)
def niceman_cfg_path(request):
    yield request.param
