# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from envconfig.config_item import ConfigurationItem
from envconfig.configuration import register_config_item
import pytest


def test_register_config_item_non_string_name():
    with pytest.raises(ValueError):
        c = ConfigurationItem(id="test")
        register_config_item(3,c)

def test_register_config_item_empty_string_name():
    with pytest.raises(ValueError):
        c = ConfigurationItem(id="test")
        register_config_item("",c)

def test_register_config_item():
    c = ConfigurationItem(id="test")
    assert(register_config_item("test",c) == 1)

