# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging

from reproman.utils import swallow_logs
from reproman.formats import Provenance


def test_get_distributions(demo1_spec):

    # Test reading the distributions from the ReproMan spec file.
    provenance = Provenance.factory(demo1_spec, 'reproman')

    with swallow_logs(new_level=logging.DEBUG) as log:
        distributions = provenance.get_distributions()
        assert len(distributions) == 2
        # a bit of testing is done within test_reproman.py since it is reproman specific example?
