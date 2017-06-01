# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from __future__ import absolute_import

import io

from pprint import pprint

from niceman.formats.niceman import NicemanspecProvenance

from .constants import NICEMAN_SPEC1_YML_FILENAME

def test_write():
    output = io.StringIO()
    # just load
    file_format = NicemanspecProvenance(NICEMAN_SPEC1_YML_FILENAME)
    env = file_format.get_environment()
    # and save
    NicemanspecProvenance.write(output, env)
    print(output.getvalue())
