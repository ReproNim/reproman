# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the NICEMAN package for the
#   copyright and license terms.
#
### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
'''Unit tests for Python API functionality.'''

import re
from niceman.utils import getargspec
import pytest

from .utils import assert_true, assert_false, eq_


def test_basic_setup():
    # the import alone will verify that all default values match their
    # constraints
    from niceman import api
    # random pick of something that should be there
    assert_true(hasattr(api, 'create'))
    assert_true(hasattr(api, 'test'))
    # make sure all helper utilities do not pollute the namespace
    # and we end up only with __...__ attributes
    assert_false(list(filter(lambda s: s.startswith('_') and not re.match('__.*__', s), dir(api))))


def get_interface_specs():
    from importlib import import_module
    from niceman.interface.base import get_interface_groups

    for grp_name, grp_descr, interfaces in get_interface_groups():
        for intfspec in interfaces:
            # turn the interface spec into an instance
            mod = import_module(intfspec[0], package='niceman')
            intf = getattr(mod, intfspec[1])
            spec = getattr(intf, '_params_', dict())

            # figure out which of the specs are "positional"
            spec_posargs = {
                name
                for name, param in spec.items()
                if param.cmd_args and not param.cmd_args[0].startswith('-')
            }
            # we have information about positional args
            yield intf, spec_posargs


interface_specs = list(get_interface_specs())


@pytest.mark.parametrize("intf,spec_posargs", interface_specs,
                         ids=[x[0].__name__ for x in interface_specs])
def test_consistent_order_of_args(intf, spec_posargs):
    f = getattr(intf, '__call__')
    args, varargs, varkw, defaults = getargspec(f)
    # now verify that those spec_posargs are first among args
    if not spec_posargs:
        pytest.skip("no positional args")
    eq_(set(args[:len(spec_posargs)]), spec_posargs)
