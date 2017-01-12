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
from niceman.provenance import Provenance

import niceman.tests.fixtures

def test_get_distributions(demo1_spec):

    # Test reading the distributions from the Repronim spec file.
    provenance = Provenance.factory(demo1_spec, 'nicemanspec')

    with swallow_logs(new_level=logging.DEBUG) as log:
        distributions = provenance.get_distributions()

        assert len(distributions) == 5

        assert distributions[0]._provenance['name'] == 'debian-1'
        assert distributions[0]._provenance['version'] == 8.5
        assert len(distributions[0]._provenance['packages']) == 2
        assert distributions[0]._provenance['packages'][0]['name'] == 'libc6-dev'
        assert distributions[0]._provenance['packages'][1]['name'] == 'python-nibabel'

        assert distributions[2]._provenance['name'] == 'neurodebian-1'
        assert distributions[2]._provenance['version'] == 8.5
        assert len(distributions[2]._provenance['packages']) == 2
        assert distributions[2]._provenance['packages'][0]['name'] == 'afni'
        assert distributions[2]._provenance['packages'][1]['name'] == 'python-nibabel'

        assert distributions[3]._provenance['name'] == 'conda-1'
        assert len(distributions[3]._provenance['packages']) == 1
        assert distributions[3]._provenance['packages'][0]['name'] == 'numpy'