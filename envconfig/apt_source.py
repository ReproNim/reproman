# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Configuration item that represents an APT source used to install packages.
   NOTE: I don't like this, and am exploring different options in
         demo_spec2.yml

"""

from __future__ import absolute_import
from six import string_types
import attr

__docformat__ = 'restructuredtext'


@attr.s
class APTSource(ConfigurationItem):
    """Configuration item that represents an APT source used to install
    packages.

    Attributes
    ----------
    id : string
        Unique identifier of the configuration item (inherited & mandatory)
    type : basestring
        Source types (i.e. "deb" or "deb-src") (mandatory)
    URI : basestring
        Base of the distribution (mandatory)
    Suite : basestring
        Distribution suite (mandatory)
    Component : basestring

    """
    id = attr.ib(validator=non_empty_string)
