# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""NICEMAN - Neuroimaging Computation Environments Manager

It is a part of the ReproNim (Reproducible Neuroimaging) suite of tools
to ease construction and execution of computation environments based on the
provenance data.
"""

from __future__ import absolute_import

from .log import lgr

# Other imports are interspersed with lgr.debug to ease troubleshooting startup
# delays etc.
lgr.log(5, "Instantiating config")
from .config import ConfigManager
cfg = ConfigManager()

# Not used (for now)
# lgr.log(5, "Instantiating ssh manager")
# from .support.sshconnector import SSHManager
# ssh_manager = SSHManager()
#
import atexit
import niceman
import os
# atexit.register(ssh_manager.close, allow_fail=False)
atexit.register(lgr.log, 5, "Exiting")

from .version import __version__


def test(package='niceman', **kwargs):
    """A helper to run niceman's tests.  Requires numpy and pytest

    See numpy.testing.Tester -- **kwargs are passed into the
    Tester().test call
    """
    import pytest
    try:
        # from numpy.testing import Tester
        # Tester(package=package).test(**kwargs)
        pytest.main(['-s', '--disable-pytest-warnings', os.path.dirname(__file__)])
        # we don't have any benchmarks atm
        # bench = Tester().bench
    except ImportError:
        raise RuntimeError('Problem with pytest for niceman.tests().  Nothing is done')
test.__test__ = False

# Following fixtures are necessary at the top level __init__ for fixtures which
# would cover all **/tests and not just niceman/tests/

# To store settings which setup_package changes and teardown_package should return
_test_states = {
    'loglevel': None,
    'NICEMAN_LOGLEVEL': None,
}

def setup_package():
    import os

    # To overcome pybuild overriding HOME but us possibly wanting our
    # own HOME where we pre-setup git for testing (name, email)
    if 'GIT_HOME' in os.environ:
        os.environ['HOME'] = os.environ['GIT_HOME']

    # To overcome pybuild by default defining http{,s}_proxy we would need
    # to define them to e.g. empty value so it wouldn't bother touching them.
    # But then haskell libraries do not digest empty value nicely, so we just
    # pop them out from the environment
    for ev in ('http_proxy', 'https_proxy'):
        if ev in os.environ and not (os.environ[ev]):
            lgr.debug("Removing %s from the environment since it is empty", ev)
            os.environ.pop(ev)

    NICEMAN_LOGLEVEL = os.environ.get('NICEMAN_LOGLEVEL', None)
    if NICEMAN_LOGLEVEL is None:
        # very very silent.  Tests introspecting logs should use
        # swallow_logs(new_level=...)
        _test_states['loglevel'] = lgr.getEffectiveLevel()
        lgr.setLevel(100)

        # And we should also set it within environ so underlying commands also stay silent
        _test_states['NICEMAN_LOGLEVEL'] = NICEMAN_LOGLEVEL
        os.environ['NICEMAN_LOGLEVEL'] = '100'
    else:
        # We are not overriding them, since explicitly were asked to have some log level
        _test_states['loglevel'] = None


def teardown_package():
    import os
    if os.environ.get('NICEMAN_TESTS_NOTEARDOWN'):
        return

    if _test_states['loglevel'] is not None:
        lgr.setLevel(_test_states['loglevel'])
        if _test_states['NICEMAN_LOGLEVEL'] is None:
            os.environ.pop('NICEMAN_LOGLEVEL')
        else:
            os.environ['NICEMAN_LOGLEVEL'] = _test_states['NICEMAN_LOGLEVEL']

    from niceman.tests import _TEMP_PATHS_GENERATED
    from niceman.tests.utils import rmtemp
    if len(_TEMP_PATHS_GENERATED):
        msg = "Removing %d dirs/files: %s" % (len(_TEMP_PATHS_GENERATED), ', '.join(_TEMP_PATHS_GENERATED))
    else:
        msg = "Nothing to remove"
    lgr.debug("Teardown tests. " + msg)
    for path in _TEMP_PATHS_GENERATED:
        rmtemp(path, ignore_errors=True)

lgr.log(5, "Done importing main __init__")
