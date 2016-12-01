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
from envconfig import configuration
import pytest

# A dict to back up the registered handlers
backup_handlers = {};

def setup_function(function):
    # Back up the registered handlers
    backup_handlers = configuration._handlers;
    configuration._handlers = {};

def teardown_function(function):
    # Restore the registered handlers
    configuration._handlers = backup_handlers;

def test_register_config_item_non_string_name():
    with pytest.raises(ValueError):
        c = ConfigurationItem(id="test")
        register_config_item(3,c)

def test_register_config_item_empty_string_name():
    with pytest.raises(ValueError):
        c = ConfigurationItem(id="test")
        register_config_item("",c)

def test_register_config_item_duplicate_handler():
    with pytest.raises(ValueError):
        c = ConfigurationItem(id="test")
        register_config_item("test",c)
        d = ConfigurationItem(id="test2")
        register_config_item("test",c)

def test_register_config_item():
    c = ConfigurationItem(id="test")
    assert(register_config_item("test",c) == 1)

