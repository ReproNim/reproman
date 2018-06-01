# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Base classes"""

import attr
from .utils import attrib


@attr.s
class BaseSpec(object):
    """Base class for all NICEMAN Specs
    
    Accent is made on providing exhaustive description of the elements
    
    Should be YAMLable
    """
    pass  # nothing in it


@attr.s
class Package(BaseSpec):
    """Base class to represent a "package" as an installable/exchangeable unit
    
    Unit comes with files which were traced to be relevant/important for a given
    computation
    """
    files = attrib(default=[])


@attr.s
class VCS(Package):
    #path = attr.ib()
    pass


@attr.s
class Git(VCS):
    pass





