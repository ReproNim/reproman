# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from mock import patch

import pytest

from reproman.tests.skip import mark
from reproman.tests.skip import skipif


def test_skipif_unknown_attribute():
    with pytest.raises(AttributeError):
        skipif.youdontknowme


def test_mark_skipif_unknown_attribute():
    with pytest.raises(AttributeError):
        mark.skipif_youdontknowme
