# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Provide information about available backend parameters.
"""

__docformat__ = 'restructuredtext'

from importlib import import_module
from logging import getLogger

from niceman.dochelpers import exc_str
from niceman.interface.base import Interface
from niceman.resource import Resource
from niceman.resource.base import ResourceManager
from niceman.resource.base import get_resource_backends
from niceman.support.constraints import EnsureStr
from niceman.support.param import Parameter


lgr = getLogger('niceman.api.backend_parameters')


def get_resource_classes(names=None):
    for name in names or ResourceManager._discover_types():
        try:
            module = import_module('niceman.resource.{}'.format(name))
        except ImportError as exc:
            import difflib
            known = ResourceManager._discover_types()
            suggestions = difflib.get_close_matches(name, known)
            lgr.warning(
                "Failed to import resource %s: %s. %s: %s",
                name,
                exc_str(exc),
                "Similar backends" if suggestions else "Known backends",
                ', '.join(suggestions or known))
            continue

        class_name = ''.join([token.capitalize() for token in name.split('_')])
        cls = getattr(module, class_name)
        if issubclass(cls, Resource):
            yield name, cls
        else:
            lgr.debug("Skipping %s.%s because it is not a Resource. "
                      "Consider moving away",
                      module, class_name)


class BackendParameters(Interface):
    """Display available backend parameters.
    """

    _params_ = dict(
        backends=Parameter(
            args=("backends",),
            metavar="BACKEND",
            doc="""Restrict output to this backend.""",
            constraints=EnsureStr(),
            nargs="*")
    )

    @staticmethod
    def __call__(backends=None):
        backends = backends or ResourceManager._discover_types()
        for backend, cls in get_resource_classes(backends):
            param_doc = "\n".join(
                ["  {}: {}".format(p, pdoc)
                 for p, pdoc in sorted(get_resource_backends(cls).items())])
            if param_doc:
                out = "Backend parameters for '{}'\n{}".format(
                    backend, param_doc)
            else:
                out = "No backend parameters for '{}'".format(backend)
            print(out)
