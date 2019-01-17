# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Tests for cmdline.helpers"""

__docformat__ = 'restructuredtext'

from ..helpers import strip_arg_from_argv

from ...tests.utils import eq_


def test_strip_arg_from_argv():
    eq_(strip_arg_from_argv(['-s', 'value'], 'value', ('-s',)), [])
    eq_(strip_arg_from_argv(['-s', 'value'], 'value', ('-s', '--long-s')), [])
    eq_(strip_arg_from_argv(
            ['cmd', '-s', 'value', '--more'], 'value', ('-s', '--long-s')),
            ['cmd',                '--more'])
