# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Common tests configuration for py.test"""

# Some commonly used fixtures

from reproman.formats.tests.fixtures import demo1_spec, reprozip_spec2
from reproman.tests.fixtures import resource_manager_fixture

import pytest


def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", default=False, help="run integration tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--integration"):
        # --integration given in cli: do not skip integration tests
        return
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


# This is useful for tests that need a ResourceManager instance but do not need
# any resources and don't plan on modifying the on-disk inventory. If you do
# need to modify the resources, use `resource_manager_fixture` directly.
resman = resource_manager_fixture(resources={}, scope="session")
