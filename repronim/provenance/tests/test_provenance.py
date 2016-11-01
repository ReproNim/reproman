# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in
from repronim.tests.test_constants import DEMO_SPEC1
from repronim.provenance import Provenance


def test_get_distributions(tmpdir):
    """
    Test reading the distributions from the Repronim spec file.
    """
    provenance_file = tmpdir.join("demo_spec1.yml")
    provenance_file.write(DEMO_SPEC1)

    provenance = Provenance.factory(provenance_file.strpath, 'repronimspec')

    with swallow_logs(new_level=logging.DEBUG) as log:
        distributions = provenance.get_distributions()

        assert len(distributions) == 5

        assert distributions[0].provenance['name'] == 'debian-1'
        assert distributions[0].provenance['version'] == 8.5
        assert len(distributions[0].provenance['packages']) == 2
        assert distributions[0].provenance['packages'][0]['name'] == 'libc6-dev'
        assert distributions[0].provenance['packages'][1]['name'] == 'python-nibabel'

        assert distributions[2].provenance['name'] == 'neurodebian-1'
        assert distributions[2].provenance['version'] == 8.5
        assert len(distributions[2].provenance['packages']) == 2
        assert distributions[2].provenance['packages'][0]['name'] == 'afni'
        assert distributions[2].provenance['packages'][1]['name'] == 'python-nibabel'

        assert distributions[3].provenance['name'] == 'conda-1'
        assert len(distributions[3].provenance['packages']) == 1
        assert distributions[3].provenance['packages'][0]['name'] == 'numpy'