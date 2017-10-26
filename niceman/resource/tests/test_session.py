# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import pytest
from ..session import get_updated_env, Session, POSIXSession
from ...support.exceptions import CommandError

@pytest.mark.skip(reason="TODO")
def test_check_envvars_handling():
    # TODO: test that all the handling of variables works with set_envvar
    # get_envvar etc
    pass


# TODO: make it into a fixture I guess if needed, or just import and call within
# specific backend tests
def check_session_passing_envvars(session):
    # TODO: do not set/pass any env variables, test that PATH is set within remote
    default_envvars = session.query_envvars()
    assert default_envvars['PATH']

    assert 'EXPORTED' not in session.query_envvars()
    session.set_envvar('EXPORTED_NOT_PERMANENT', 'VALUE')
    assert session.query_envvars()['EXPORTED_NOT_PERMANENT'] == 'VALUE'

    session.set_envvar('EXPORTED_PERMANENT', 'VALUE2')
    assert session.query_envvars()['EXPORTED_NOT_PERMANENT'] == 'VALUE'
    assert session.query_envvars()['EXPORTED_PERMANENT'] == 'VALUE2'

    # TODO: we should add functionality to record the state of the env
    # upon finishing create (or install? login?) and here could test
    # smth like
    #  session = session.restart()
    #  envvars = assert session.query_envvars()
    #  assert 'EXPORTED_NOT_PERMANENT' not in envvars
    #  assert envvars['EXPORTED_NOT_PERMANENT'] == 'VALUE2'


def test_get_updated_env():
    assert get_updated_env({'a': 1}, {'a': 2}) == {'a': 2}
    assert get_updated_env({'a': None}, {'a': 2}) == {'a': 2}
    assert get_updated_env({'a': 1}, {'a': None}) == {}
    assert get_updated_env({'a': 1, 'b': 2}, {'a': None}) == {'b': 2}
    assert get_updated_env({'a': 1, 'b': 2}, {'a': None, 'b': 3}) == {'b': 3}
