# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Facility for managing compute resources.

"""

__docformat__ = 'restructuredtext'

from .base import Resource, ResourceManager

_MANAGER = None


def get_manager():
    """Return a ResourceManager instance.

    A new instance is not created if one already exists.  This getter function
    is used rather than a module-level instance to support delaying instance
    creation.
    """
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ResourceManager()
    return _MANAGER
