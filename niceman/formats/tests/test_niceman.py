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

from niceman.formats.niceman import NicemanProvenance

from .constants import NICEMAN_SPEC1_YML_FILENAME


def test_write():
    output = io.StringIO()
    # just load
    file_format = NicemanProvenance(NICEMAN_SPEC1_YML_FILENAME)
    env = file_format.get_environment()
    # just a basic test that we loaded stuff correctly
    assert len(env.distributions) == 2
    assert env.distributions[0].name == 'conda'
    assert len(env.distributions[1].apt_sources) == 3
    # and save
    NicemanProvenance.write(output, env)
    out = output.getvalue()
    env_reparsed = NicemanProvenance(out).get_environment()
    # and we could do the full round trip while retaining the same "value"
    assert env == env_reparsed
    print(out)
