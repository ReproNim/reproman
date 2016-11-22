# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Configuration item that represents a distribution used to install packages

"""

from __future__ import absolute_import
from six import string_types
import attr

__docformat__ = 'restructuredtext'


@attr.s
class Distribution(ConfigurationItem):
    """Configuration item that represents a distribution to install packages

    Attributes
    ----------
    id : string
        Unique identifier of the configuration item (inherited)
    name: basestring
    origin: basestring
    label: basestring
    suite: basestring
    version: basestring
    

    """
    id = attr.ib(validator=non_empty_string)
