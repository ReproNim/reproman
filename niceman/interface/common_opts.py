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

trace_opt = Parameter(
    args=("--trace",),
    action="store_true",
    doc="""if set, trace execution within the environment""")

resource_name_opt = Parameter(
    args=("-n", "--name",),
    doc="Name of the environment container",
    constraints=EnsureStr() | EnsureNone())

resource_id_opt = Parameter(
    args=("-id", "--resource-id",),
    doc="ID of the environment container",
    constraints=EnsureStr() | EnsureNone())
