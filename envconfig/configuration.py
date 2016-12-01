# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Coordination for ReproNim environment configuration handlers

"""

from __future__ import absolute_import
from six import string_types
import attr

from envconfig.config_item import ConfigurationItem

# A dict of registered handlers. The keys are cnfiguration names (used
# for case-insensitive matching with the configuration file).  The
# values are registered subclasses of ConfigurationItem.
_handlers = {}

def register_config_item(name, handler_class):
    """Register a config_item class

    Registers a subclass of ConfigurationItem to provide and handle
    configuration items of the given name (using case insensitive
    matching)

    Parameters
    ----------
    name : string
        The YAML configuration tag handled by the class

    handler_class : ConfigurationItem
        The handler

    Return
    ------

    Raises
    ------
    ValueError
        If the parameter types are incorrect

    """

    if not(isinstance(name, string_types)):
        raise ValueError("'name' must be a string.")
    if not name:
        raise ValueError("'name' must not be empty.")
    if not(isinstance(handler_class, ConfigurationItem)):
        raise ValueError("'handler_class' must be ConfigurationItem.")
    if (name in _handlers):
        raise ValueError("A handler for '{0}' has already been defined.".format(name))

    _handlers[name] = handler_class;

    return(len(_handlers))


