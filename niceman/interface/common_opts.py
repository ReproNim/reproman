# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Common interface options

"""

__docformat__ = 'restructuredtext'

from niceman.support.param import Parameter
from niceman.support.constraints import EnsureInt, EnsureNone, EnsureStr


#
# Resource specifications
#

# This is a positional argument...
resource_arg = Parameter(
    args=("resource",),
    nargs="?",
    doc="""Name of the resource to consider. To see
    available resource, run the command 'niceman ls'""",
    constraints=EnsureStr() | EnsureNone()
)

resource_name_opt = Parameter(
    args=("--resource-name",),
    doc="Name of the environment container",
    constraints=EnsureStr() | EnsureNone()
)

resource_id_opt = Parameter(
    args=("-id", "--resource-id",),
    doc="ID of the environment container",
    constraints=EnsureStr() | EnsureNone()
)

# XXX thought to combine 3 above into a single entry to ease
# reuse but wouldn't be possible to use ATM since _params is a dict
# and we can't easily "add" dicts
#resouce_spec = []

# XXX reenable when we support working with multiple instances at once
resource_type_opt = Parameter(
    args=("-t", "--resource-type"),
    doc="""Resource type to work on""",
    constraints=EnsureStr(),
)