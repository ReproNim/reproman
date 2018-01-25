# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os
import pytest
import tempfile
from .constants import NICEMAN_CFG_PATH

# Substitutes in for user's ~/.config/niceman.cfg file
CONFIGURATION = [
    NICEMAN_CFG_PATH
]

@pytest.fixture(params=CONFIGURATION)
def niceman_cfg_path(request):
    yield request.param


class FixtureTempFile:
	"""Utility class for the "temp_file" pytest fixture to help manage the
	temporary file.
	
	Attributes
	----------
	_fd : int
		File descriptor id of temp file
	_path : str
		Path to temp file
	"""
	def __init__(self, fid, path):
		self.fid = fid
		self.path = path
	def __call__(self, content):
		if content:
			file = open(self.path, "w")
			file.write(content)
			file.close()
	def __repr__(self):
		return self.path

@pytest.fixture(scope="module")
def temp_file():
	"""Provide an empty temporary file for a test.
	
	The fixture will create a temp file and remove it when the test is complete.
	To add content to the temporary file, call the object in the test function
	with the content passed as the first argument of the call.

	e.g. tmp_file("my content")

	Returns
	-------
	FixtureTempFile object
	"""
	fid, path = tempfile.mkstemp()
	temp_file = FixtureTempFile(fid, path)
	yield temp_file
	os.remove(path)
