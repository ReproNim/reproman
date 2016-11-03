# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from envconfig.config_item import ConfigurationItem
from nose.tools import *


@raises(ValueError)
def test_config_item_non_string_id():
    r"""Test config item with non string id"""
    ConfigurationItem(id=3)


@raises(ValueError)
def test_config_item_empty_string():
    r"""Test config item with empty string"""
    ConfigurationItem(id="")


def test_config_item_valid_id():
    r"""Test config item with valid string"""
    assert(ConfigurationItem(id="test"))
