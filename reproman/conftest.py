# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Common tests configuration for py.test
"""

# Some commonly used fixtures

from niceman.formats.tests.fixtures import demo1_spec, reprozip_spec2

import pytest


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true",
                     default=False, help="run integration tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--integration"):
        # --integration given in cli: do not skip integration tests
        return
    skip_integration = pytest.mark.skip(
        reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
