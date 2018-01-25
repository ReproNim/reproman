# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ..base import EnvironmentSpec

import os
from nose.tools import assert_raises
import pytest

from niceman.formats.niceman import NicemanProvenance

@pytest.fixture
def envs():
    env1_fname = os.path.join(os.path.dirname(__file__), 'files', 'env1.yaml')
    env2_fname = os.path.join(os.path.dirname(__file__), 'files', 'env2.yaml')
    prov1 = NicemanProvenance(env1_fname)
    prov2 = NicemanProvenance(env2_fname)
    return (prov1.get_environment(), prov2.get_environment())

def test_sub_basic(envs):
    env = envs[0]
    assert_raises(TypeError, lambda: env-None)
    denv = env-env
    assert isinstance(denv, EnvironmentSpec)
    assert denv.base is None
    assert denv.distributions == []
    assert denv.files == []

def test_sub(envs):
    (env1, env2) = envs
    denv = env2-env1
    assert denv.base is None
    assert denv.files == ['/usr/lib/locale/locale-archive']
    # WIP; will fail
    assert denv.distributions
