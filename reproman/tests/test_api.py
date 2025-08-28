# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the ReproMan package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Unit tests for Python API functionality."""

import os
import re
import sys

from ..utils import getargspec
from ..cmd import Runner

import pytest
from .utils import assert_true, assert_false, eq_


def test_basic_setup():
    # the import alone will verify that all default values match their
    # constraints
    from reproman import api

    # random pick of something that should be there
    assert_true(hasattr(api, "create"))
    assert_true(hasattr(api, "test"))
    # make sure all helper utilities do not pollute the namespace
    # and we end up only with __...__ attributes
    assert_false(list(filter(lambda s: s.startswith("_") and not re.match("__.*__", s), dir(api))))


def get_interface_specs():
    from importlib import import_module
    from reproman.interface.base import get_interface_groups

    for grp_name, grp_descr, interfaces in get_interface_groups():
        for intfspec in interfaces:
            # turn the interface spec into an instance
            mod = import_module(intfspec[0], package="reproman")
            intf = getattr(mod, intfspec[1])
            spec = getattr(intf, "_params_", dict())

            # figure out which of the specs are "positional"
            spec_posargs = {
                name for name, param in spec.items() if param.cmd_args and not param.cmd_args[0].startswith("-")
            }
            # we have information about positional args
            yield intf, spec_posargs


interface_specs = list(get_interface_specs())


@pytest.mark.parametrize("intf,spec_posargs", interface_specs, ids=[x[0].__name__ for x in interface_specs])
def test_consistent_order_of_args(intf, spec_posargs):
    f = getattr(intf, "__call__")
    args, varargs, varkw, defaults = getargspec(f)
    # now verify that those spec_posargs are first among args
    if not spec_posargs:
        pytest.skip("no positional args")
    eq_(set(args[: len(spec_posargs)]), spec_posargs)


def test_no_heavy_imports():

    def get_modules(extra=""):
        out, err = Runner().run([sys.executable, "-c", "import os, sys%s; print(os.linesep.join(sys.modules))" % extra])
        return set(out.split(os.linesep))

    # Establish baseline
    modules0 = get_modules()  # e.g. currently ~60

    # new modules brought by import of our .api
    modules = get_modules(", reproman.api").difference(modules0)
    # TODO: add back whenever/if https://github.com/sensein/etelemetry-client/issues/29
    # is properly addressed
    # assert 'requests' not in modules
    # assert len(modules) < 230  # currently 203
    assert "boto" not in modules
    assert "jinja2" not in modules
    assert "paramiko" not in modules
    # and catch it all!  Raise the boundary as needed
    assert len(modules) < 600  # currently could be 508 with requests due to etelemetry
