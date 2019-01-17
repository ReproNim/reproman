# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Common tests configuration for resources
"""

from appdirs import AppDirs
import os
import pytest
import shutil


@pytest.fixture(scope="module")
def resource_test_dir():
	dirs = AppDirs('niceman')
	test_dir = os.path.join(dirs.user_cache_dir, 'resource_test')
	if not os.path.exists(test_dir):
		os.makedirs(test_dir)
	yield test_dir
	shutil.rmtree(test_dir)
