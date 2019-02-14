# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Tests for run and jobs interfaces.
"""

import pytest
from six import text_type

from reproman.api import run
from reproman.utils import swallow_outputs


def test_run_no_command():
    with pytest.raises(ValueError) as exc:
        run()
    assert "No command" in text_type(exc)


def test_run_no_resource():
    with pytest.raises(ValueError) as exc:
        run(command="blahbert")
    assert "No resource" in text_type(exc)


def test_run_list():
    with swallow_outputs() as output:
        run(list_=True)
        assert "local" in output.out
        assert "plain" in output.out
