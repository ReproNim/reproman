# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ..reprozip import ReprozipProvenance
from .constants import REPROZIP_SPEC2_YML_FILENAME


def test_load_config():
    config = ReprozipProvenance(REPROZIP_SPEC2_YML_FILENAME)
    files_all = config.get_files()
    files_noother = config.get_files(limit='other')
    assert len(files_noother) < len(files_all)
    # TODO: more testing

