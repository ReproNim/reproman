# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to represent high-level configuration items

"""

from __future__ import absolute_import
import attr

__docformat__ = 'restructuredtext'


def non_empty_string(instance, attribute, value):
    r"""attr.ib validator to ensure it is a non-empty string"""
    if not(isinstance(value, basestring)):
        raise ValueError("'id' must be a string.")
    if not value:
        raise ValueError("'id' must not be empty.")


@attr.s
class ConfigurationItem(object):
    r"""Parent class to represent configuration items that define an experiment
    environment such as packages, files, environment variables, and commands.

    Attributes
    ----------
    id : string
         Unique identifier of the configuration item

    """
    id = attr.ib(validator=non_empty_string)