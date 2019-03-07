# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the ReproMan package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""tests for dialog UI """

__docformat__ = 'restructuredtext'

from io import StringIO
import builtins

from unittest.mock import patch
import pytest

from ...tests.utils import eq_
from ...tests.utils import assert_raises
from ...tests.utils import assert_re_in
from ...tests.utils import assert_in
from ...tests.utils import ok_startswith
from ...tests.utils import ok_endswith
from ..dialog import DialogUI
from reproman.ui.progressbars import progressbars


def patch_input(**kwargs):
    """A helper to provide mocked cm patching input function which was renamed in PY3"""
    return patch.object(builtins, 'input', **kwargs)


def patch_getpass(**kwargs):
    return patch('getpass.getpass', **kwargs)


def test_question_choices():

    # TODO: come up with a reusable fixture for testing here

    choices = {
        'a': '[a], b, cc',
        'b': 'a, [b], cc',
        'cc': 'a, b, [cc]'
    }

    for default_value in ['a', 'b']:
        choices_str = choices[default_value]
        for entered_value, expected_value in [(default_value, default_value),
                                              ('', default_value),
                                              ('cc', 'cc')]:
            with patch_getpass(return_value=entered_value), \
                patch_getpass(return_value=entered_value):
                out = StringIO()
                response = DialogUI(out=out).question("prompt", choices=sorted(choices), default=default_value)
                eq_(response, expected_value)
                # getpass doesn't use out -- goes straight to the terminal
                eq_(out.getvalue(), '')
                # TODO: may be test that the prompt was passed as a part of the getpass arg
                #eq_(out.getvalue(), 'prompt (choices: %s): ' % choices_str)

    # check some expected exceptions to be thrown
    out = StringIO()
    ui = DialogUI(out=out)
    assert_raises(ValueError, ui.question, "prompt", choices=['a'], default='b')
    eq_(out.getvalue(), '')

    with patch_getpass(return_value='incorrect'):
        assert_raises(RuntimeError, ui.question, "prompt", choices=['a', 'b'])
    assert_re_in(".*ERROR: .incorrect. is not among choices.*", out.getvalue())


@pytest.mark.parametrize("backend", progressbars)
@pytest.mark.parametrize("l", [0, 4, 10, 1000])
@pytest.mark.parametrize("increment", [True, False])
def test_progress_bar(backend, l, increment):
    out = StringIO()
    fill_str = ('123456890' * (l//10))[:l]
    pb = DialogUI(out).get_progressbar('label', fill_str, maxval=10, backend=backend)
    pb.start()
    # we can't increment 11 times
    for x in range(11):
        if not (increment and x == 0):
            # do not increment on 0
            pb.update(x if not increment else 1, increment=increment)
        out.flush()  # needed atm
        pstr = out.getvalue()
        ok_startswith(pstr.lstrip('\r'), 'label:')
        assert_re_in(r'.*\b%d%%.*' % (10*x), pstr)
        if backend == 'progressbar':
            assert_in('ETA', pstr)
    pb.finish()
    ok_endswith(out.getvalue(), '\n')
