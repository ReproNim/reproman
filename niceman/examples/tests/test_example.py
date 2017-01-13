# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the NICEMAN package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Test functionality of example.py

"""

from niceman.examples.example import get_url_for_packages

__docformat__ = 'restructuredtext'

# from niceman.examples.example import
from niceman.tests.utils import assert_equal


def test_get_url_for_packages():
    assert_equal(get_url_for_packages({'cmtk': '3.2'}), {'cmtk': 'http://example.com/cmtk_3.2.deb'})
    assert_equal(get_url_for_packages(
        {'cmtk': '3.1'}), {'cmtk': 'http://example.com/cmtk_3.1.deb'})