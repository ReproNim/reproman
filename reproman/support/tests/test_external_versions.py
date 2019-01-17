# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging

from os import linesep

from ... import __version__
from ...dochelpers import exc_str
from ...version import __version__
from ..external_versions import ExternalVersions, LooseVersion
from ...tests.utils import assert_true, assert_false
from ...tests.utils import assert_equal, assert_greater_equal, assert_greater
from ..exceptions import CommandError
from ..exceptions import OutdatedExternalDependency, MissingExternalDependency
from ...tests.utils import (
    with_tempfile,
    create_tree,
    swallow_logs,
)

import pytest
from mock import patch
from six import PY3

if PY3:
    # just to ease testing
    def cmp(a, b):
        return (a > b) - (a < b)


def test_external_versions_basic():
    ev = ExternalVersions()
    our_module = 'niceman'
    assert_equal(ev.versions, {})
    assert_equal(ev[our_module], __version__)
    # and it could be compared
    assert_greater_equal(ev[our_module], __version__)
    assert_greater(ev[our_module], '0.0.0a1')
    assert_equal(list(ev.keys()), [our_module])
    assert_true(our_module in ev)
    assert_false('unknown' in ev)

    # all are LooseVersions now
    assert_true(isinstance(ev[our_module], LooseVersion))
    version_str = __version__
    assert_equal(ev.dumps(), "Versions: %s=%s" % (our_module, version_str))

    # For non-existing one we get None
    assert_equal(ev['custom__nonexisting'], None)
    # and nothing gets added to _versions for nonexisting
    assert_equal(set(ev.versions.keys()), {our_module})

    # but if it is a module without version, we get it set to UNKNOWN
    assert_equal(ev['os'], ev.UNKNOWN)
    # And get a record on that inside
    assert_equal(ev.versions.get('os'), ev.UNKNOWN)
    # And that thing is "True", i.e. present
    assert(ev['os'])
    # but not comparable with anything besides itself (was above)
    pytest.raises(TypeError, cmp, ev['os'], '0')
    pytest.raises(TypeError, assert_greater, ev['os'], '0')

    return
    # Code below is from original duecredit, and we don't care about
    # testing this one
    # And we can get versions based on modules themselves
    from niceman.tests import mod
    assert_equal(ev[mod], mod.__version__)

    # Check that we can get a copy of the versions
    versions_dict = ev.versions
    versions_dict[our_module] = "0.0.1"
    assert_equal(versions_dict[our_module], "0.0.1")
    assert_equal(ev[our_module], __version__)


def test_external_version_contains():
    ev = ExternalVersions()
    assert_true("niceman" in ev)
    assert_false("does not exist" in ev)


def test_external_versions_unknown():
    assert_equal(str(ExternalVersions.UNKNOWN), 'UNKNOWN')


def test_external_versions_smoke():
    ev = ExternalVersions()
    assert_false(linesep in ev.dumps())
    assert_true(ev.dumps(indent=True).endswith(linesep))


@pytest.mark.parametrize("modname",
                         ['scipy', 'numpy', 'mvpa2', 'sklearn', 'statsmodels',
                          'pandas', 'matplotlib', 'psychopy'])
def test_external_versions_popular_packages(modname):
    ev = ExternalVersions()
    try:
        exec("import %s" % modname, globals(), locals())
    except ImportError:
        pytest.skip("External %s not present" % modname)
    except Exception as e:
        pytest.skip("External %s fails to import: %s" % (modname, exc_str(e)))
    assert (ev[modname] is not ev.UNKNOWN)
    assert_greater(ev[modname], '0.0.1')
    assert_greater('1000000.0', ev[modname])  # unlikely in our lifetimes


def test_external_versions_rogue_module(tmpdir):
    topd = str(tmpdir)
    ev = ExternalVersions()
    # if module throws some other non-ImportError exception upon import
    # we must not crash, but issue a warning
    modname = 'verycustomrogue__'
    create_tree(topd, {modname + '.py': 'raise Exception("pickaboo")'})
    with patch('sys.path', [topd]), \
        swallow_logs(new_level=logging.WARNING) as cml:
        assert ev[modname] is None
        assert_true(ev.dumps(indent=True).endswith(linesep))
        assert 'pickaboo' in cml.out


def test_custom_versions():
    ev = ExternalVersions()
    ev.CUSTOM = {'bogus': lambda: 1 / 0}
    assert_equal(ev['bogus'], None)


class thing_with_tuple_version:
    __version__ = (0, 1)


class thing_with_list_version:
    __version__ = [0, 1]


@pytest.mark.parametrize("thing",
                         [thing_with_tuple_version, thing_with_list_version,
                          '0.1', (0, 1), [0, 1]])
def test_list_tuple(thing):
    version = ExternalVersions._deduce_version(thing)
    assert_greater(version, '0.0.1')
    assert_greater('0.2', version)
    assert_equal('0.1', version)
    assert_equal(version, '0.1')


def test_humanize():
    # doesn't provide __version__
    assert ExternalVersions()['humanize']


def test_check():
    ev = ExternalVersions()
    # should be all good
    ev.check('niceman')
    ev.check('niceman', min_version=__version__)

    with pytest.raises(MissingExternalDependency):
        ev.check('dataladkukaracha')
    with pytest.raises(MissingExternalDependency) as cme:
        ev.check('dataladkukaracha', min_version="buga", msg="duga")

    assert "duga" in str(cme.value)

    with pytest.raises(OutdatedExternalDependency):
        ev.check('niceman', min_version="10000000")  # we will never get there!
