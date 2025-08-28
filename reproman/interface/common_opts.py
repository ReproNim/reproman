# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Common interface options"""

__docformat__ = "restructuredtext"

from reproman.support.param import Parameter
from reproman.support.constraints import EnsureChoice
from reproman.support.constraints import EnsureInt, EnsureNone, EnsureStr


trace_opt = Parameter(args=("--trace",), action="store_true", doc="""if set, trace execution within the environment""")


#
# Resource specifications
#

resref_arg = Parameter(
    args=("resref",),
    metavar="RESOURCE",
    doc="""Name or ID of the resource to operate on. To see available resources, run
    'reproman ls'""",
    constraints=EnsureStr() | EnsureNone(),
)

resref_opt = Parameter(
    args=(
        "-r",
        "--resource",
    ),
    dest="resref",
    metavar="RESOURCE",
    doc="""Name or ID of the resource to operate on. To see available resources, run
    'reproman ls'""",
    constraints=EnsureStr() | EnsureNone(),
)

resref_type_opt = Parameter(
    args=("--resref-type",),
    metavar="TYPE",
    doc="""A resource can be referenced by its name or ID.  In the unlikely
    case that a name collides with an ID, explicitly specify 'name' or 'id' to
    disambiguate.""",
    constraints=EnsureChoice("auto", "name", "id"),
)
