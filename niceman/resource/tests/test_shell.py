# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
import os
from pytest import raises
from mock import patch, call

from ...utils import swallow_logs
from ...tests.utils import with_tempfile
from ...tests.utils import assert_in
from ..base import ResourceManager
from ...cmd import Runner
from ..shell import Shell, ShellSession
from .test_session import check_session_passing_envvars


def test_shell_class():

    with patch.object(Runner, 'run', return_value='installed package') as runner, \
            swallow_logs(new_level=logging.DEBUG) as log:

        # Test running some install commands.
        config = {
            'name': 'my-shell',
            'type': 'shell'
        }
        shell = ResourceManager.factory(config)

        command = ['apt-get', 'install', 'bc']
        shell.add_command(command)
        command = ['apt-get', 'install', 'xeyes']
        shell.add_command(command)
        shell.execute_command_buffer()
        common_kwargs = dict(cwd=None, expect_fail=True, expect_stderr=True)
        calls = [
            call(['apt-get', 'install', 'xeyes'], **common_kwargs),
            call(['apt-get', 'install', 'bc'], **common_kwargs),
        ]
        runner.assert_has_calls(calls, any_order=True)
        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['apt-get', 'install', 'xeyes']'", log.lines)


@with_tempfile(content="""
echo "Enabling special environment"
echo "We could even spit out an stderr output">&2
export EXPORTED_VAR="
multiline
"
export PATH=/custom:$PATH
NON_EXPORTED_VAR=2         # but may be those should be handled??
""")
def test_source_file(script=None):
    ses = ShellSession()
    assert ses.get_envvars() == {}
    new_env_diff = ses.source_script(script, diff=True)
    assert len(new_env_diff) == 2
    assert new_env_diff['PATH'].startswith('/custom:')
    assert new_env_diff['EXPORTED_VAR'] == "\nmultiline\n"


@with_tempfile(content="exit 1")
def test_source_file_crash(script=None):
    ses = ShellSession()
    with raises(Exception):  # TODO: unify?
        ses.source_script(script)


@with_tempfile(content="""
if ! [ "$1" = "test" ]; then
   exit 1
fi
export EXPORTED_VAR=${1}1
NON_EXPORTED_VAR=2         # but may be those should be handled??
""")
def test_source_file_param(script=None):
    ses = ShellSession()
    assert ses.get_envvars() == {}
    new_env_diff = ses.source_script([script, "test"])
    assert new_env_diff == {'EXPORTED_VAR': 'test1'}

    new_env_diff = ses.source_script([script, "test"],
                                     shell="/bin/bash")
    assert new_env_diff == {}

    # just for "fun"
    #print ses.source_script([os.path.expanduser('~/anaconda2/bin/activate'), 'datalad'])


def test_session_passing_envvars():
    check_session_passing_envvars(ShellSession())