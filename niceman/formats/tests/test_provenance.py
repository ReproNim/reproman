# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging

from niceman.utils import swallow_logs
from niceman.formats import Provenance


def test_get_distributions(demo1_spec):

    # Test reading the distributions from the NICEMAN spec file.
    provenance = Provenance.factory(demo1_spec, 'niceman')

    with swallow_logs(new_level=logging.DEBUG) as log:
        distributions = provenance.get_distributions()
        assert len(distributions) == 2
        # a bit of testing is done within test_niceman.py since it is niceman specific example?
