# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from unittest.mock import patch

import pytest

from reproman.tests.skip import Mark
from reproman.tests.skip import mark
from reproman.tests.skip import skipif


with patch.dict("os.environ", {"REPROMAN_TESTS_NONETWORK": "1"}):
    @mark.skipif_no_network
    def test_mark_skipif_always_skip():
        assert False, "This test should never run"


def test_skipif_inline():
    with patch.dict("os.environ", {"REPROMAN_TESTS_NONETWORK": "1"}):
        with pytest.raises(pytest.skip.Exception):
            skipif.no_network()


def test_skipif_no_ssh():
    with patch.dict("os.environ", {"REPROMAN_TESTS_SSH": "1"}):
        try:
            skipif.no_ssh()
        except pytest.skip.Exception as exc:
            assert 0, "Test should not have been skipped"

        # We skip SSH on windows even when REPROMAN_TESTS_SSH is set.
        with patch("reproman.tests.skip._on_windows", True):
            with pytest.raises(pytest.skip.Exception):
                skipif.no_ssh()


def test_skipif_unknown_attribute():
    with pytest.raises(AttributeError):
        skipif.youdontknowme


def test_mark_skipif_unknown_attribute():
    with pytest.raises(AttributeError):
        mark.skipif_youdontknowme


def test_other_attribute_error():
    # If a condition function raises an AttributeError, Mark doesn't mistake it
    # for an unknown condition function.

    def no_confusion():
        raise AttributeError("don't get confused")

    with patch("reproman.tests.skip.Namespace.fns",
               {"no_confusion": no_confusion}):
        with pytest.raises(AttributeError) as exc:
            m = Mark()
            m.skipif_no_confusion
            assert "don't get confused" in str(exc.value)
