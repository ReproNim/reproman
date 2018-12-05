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
import pytest
import re
import tempfile
from pytest import raises
from mock import patch, call

from ...utils import swallow_logs
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


def test_source_file(resource_test_dir):

    # Create a temporary test file
    temp_file = tempfile.NamedTemporaryFile(dir=resource_test_dir)
    with temp_file as f:
        f.write("""
echo "Enabling special environment"
echo "We could even spit out an stderr output">&2
export EXPORTED_VAR="
multiline
"
export PATH=/custom:$PATH
NON_EXPORTED_VAR=2         # but may be those should be handled??
    """.encode('utf8'))
        f.flush()
        script = temp_file.name
        session = ShellSession()
        assert session.get_envvars() == {}
        new_env_diff = session.source_script(script, diff=True)
        assert 'EXPORTED_VAR' in new_env_diff
        assert new_env_diff['PATH'].startswith('/custom:')
        assert new_env_diff['EXPORTED_VAR'] == "\nmultiline\n"


def test_source_file_crash(resource_test_dir):
    temp_file = tempfile.NamedTemporaryFile(dir=resource_test_dir)
    with temp_file as f:
        f.write('exit 1'.encode('utf8'))
        f.flush()
        script = temp_file.name
        session = ShellSession()
        with raises(Exception):  # TODO: unify?
            session.source_script(script)


def test_isdir():
    session = ShellSession()
    assert not session.isdir(__file__)
    assert session.isdir("/bin")


def test_exists():
    session = ShellSession()
    (_, name) = tempfile.mkstemp()
    assert session.exists(name)
    os.remove(name)
    assert not session.exists(name)
    assert session.exists("/bin")


def test_source_file_param(resource_test_dir):
    temp_file = tempfile.NamedTemporaryFile(dir=resource_test_dir)
    with temp_file as f:
        f.write("""
if ! [ "$1" = "test" ]; then
   exit 1
fi
export EXPORTED_VAR=${1}1
NON_EXPORTED_VAR=2         # but may be those should be handled??
    """.encode('utf8'))
        f.flush()
        script = temp_file.name
        session = ShellSession()
        assert session.get_envvars() == {}
        new_env_diff = session.source_script([script, "test"])
        assert 'EXPORTED_VAR' in new_env_diff
        assert new_env_diff['EXPORTED_VAR'] == 'test1'

        new_env_diff = session.source_script([script, "test"],
                                         shell="/bin/bash")
        assert new_env_diff == {}


def test_session_passing_envvars():
    check_session_passing_envvars(ShellSession())


def test_shell_resource():

    config = {
        'name': 'test-ssh-resource',
        'type': 'shell'
    }
    resource = ResourceManager.factory(config)

    status = resource.create()
    assert re.match('\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$', status['id']) is not None

    assert type(resource.connect()) == Shell
    assert resource.delete() is None
    with pytest.raises(NotImplementedError):
        resource.start()
    with pytest.raises(NotImplementedError):
        resource.stop()
    assert type(resource.connect()) == Shell

    with raises(NotImplementedError):
        resource.get_session(pty=True)
    with raises(NotImplementedError):
        resource.get_session(pty=False, shared=True)
