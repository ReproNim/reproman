# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Provide information about available backend parameters."""

__docformat__ = "restructuredtext"

from logging import getLogger

from reproman.dochelpers import exc_str
from reproman.interface.base import Interface
from reproman.resource import Resource
from reproman.resource.base import discover_types
from reproman.resource.base import get_resource_backends
from reproman.resource.base import get_resource_class
from reproman.support.constraints import EnsureStr
from reproman.support.exceptions import ResourceError
from reproman.support.param import Parameter


lgr = getLogger("reproman.api.backend_parameters")


def get_resource_classes(names=None):
    for name in names or discover_types():
        try:
            cls = get_resource_class(name)
        except ResourceError as exc:
            lgr.warning(exc_str(exc))
            continue

        if issubclass(cls, Resource):
            yield name, cls
        else:
            lgr.debug("Skipping %s because it is not a Resource. " "Consider moving away", cls)


class BackendParameters(Interface):
    """Display available backend parameters."""

    _params_ = dict(
        backends=Parameter(
            args=("backends",),
            metavar="BACKEND",
            doc="""Restrict output to this backend.""",
            constraints=EnsureStr(),
            nargs="*",
        )
    )

    @staticmethod
    def __call__(backends=None):
        backends = backends or discover_types()
        for backend, cls in get_resource_classes(backends):
            param_doc = "\n".join(
                ["  {}: {}".format(p, pdoc) for p, pdoc in sorted(get_resource_backends(cls).items())]
            )
            if param_doc:
                out = "Backend parameters for '{}'\n{}".format(backend, param_doc)
            else:
                out = "No backend parameters for '{}'".format(backend)
            print(out)
