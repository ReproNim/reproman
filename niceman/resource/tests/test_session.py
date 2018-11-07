# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import datetime
import docker
import logging
import os
from fabric import Connection
import pytest
import tempfile
import uuid

from ..session import get_updated_env, Session
from ...support.exceptions import CommandError
from ..docker_container import DockerSession, PTYDockerSession
from ...utils import chpwd, swallow_logs
from ..shell import ShellSession
from ..singularity import Singularity, SingularitySession, \
    PTYSingularitySession
from ..ssh import SSHSession, PTYSSHSession
from ...tests.utils import skip_ssh
from ...tests.fixtures import get_docker_fixture
from ...consts import TEST_SSH_DOCKER_DIGEST


# Note: due to skip_ssh right here, it would skip the entire module with
# all the tests here if no ssh testing is requested
testing_container = skip_ssh(get_docker_fixture)(
    TEST_SSH_DOCKER_DIGEST,
    name='testing-container',
    portmaps={
        49000: 22
    },
    custom_params={
        'host': 'localhost',
        'user': 'root',
        'port': 49000,
    },
    scope='module'
)


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


def test_get_local_session():
    # get_local_session(env={'LC_ALL': 'C'}, pty=False, shared=None)
    return


def test_session_class():

    with Session() as session:

        # Check class constructor
        assert type(session) == Session

        # Check __call__ is passing through to _execute_command()
        with pytest.raises(NotImplementedError):
            stdout, stderr = session(['ls'], env={'ENV_VAR': 'ENV_VALUE'})

        session._env = { 'VAR': 'VAR_VALUE' }
        session._env_permanent = { 'PERM_VAR': 'PERM_VAR_VALUE' }

        # Check we can read _envs properly
        envvars = session.get_envvars()
        assert envvars['VAR'] == 'VAR_VALUE'
        assert 'PERM_VAR' not in envvars

        # Check we can read permanent envs
        envvars = session.get_envvars(permanent=True)
        assert envvars['PERM_VAR'] == 'PERM_VAR_VALUE'
        assert 'VAR' not in envvars

        # Check we can add an env through the setter
        session.set_envvar('NEW_VAR', value='NEW_VAR_VALUE')
        envvars = session.get_envvars()
        assert envvars['NEW_VAR'] == 'NEW_VAR_VALUE'
        assert envvars['VAR'] == 'VAR_VALUE'

        # Check we can set an env var by passing a dict
        session.set_envvar({'DICT_VAR': 'DICT_VAR_VALUE'})
        envvars = session.get_envvars()
        assert envvars['DICT_VAR'] == 'DICT_VAR_VALUE'
        assert envvars['VAR'] == 'VAR_VALUE'

        # Check we can delete an existing env var
        session.set_envvar('DICT_VAR', None)
        envvars = session.get_envvars()
        assert 'DICT_VAR' not in envvars
        assert envvars['VAR'] == 'VAR_VALUE'

        # Check formatting of env values
        session.set_envvar('VAR', 'FORMATTED {}', format=True)
        envvars = session.get_envvars()
        assert envvars['VAR'] == 'FORMATTED VAR_VALUE' 
        assert envvars['NEW_VAR'] == 'NEW_VAR_VALUE'

        # At this time, setting permanent env vars is not supported
        with pytest.raises(NotImplementedError):
            session.set_envvar('NEW_VAR', value='NEW_VAR_VALUE',
                permanent=True)

        # Check we raise an exception if user tries to set an env value while
        # passing a dict
        with pytest.raises(AssertionError):
            session.set_envvar({'WILL': 'FAIL'}, value='!')

        # Check query_envvars() method not implemented
        with pytest.raises(NotImplementedError):
            session.query_envvars()

        # Check source_script() method not implemented
        with pytest.raises(NotImplementedError):
            session.source_script(['ls'])

        # Check unauthorized commands raise CommandError exception
        with pytest.raises(CommandError):
            session.niceman_exec('sudo', ['rm', '-r', '/'])

        # Check mangled arg raises exception
        with pytest.raises(CommandError):
            session.niceman_exec('mkdir', ['bad=passed=argument'])

        # Check exec command to valid method passes through to not implemented
        # exception
        with pytest.raises(NotImplementedError):
            session.niceman_exec('mkdir', ['/my/new/dir', 'parents=True'])

        # Check abstract methods raise NotImplementedError
        with pytest.raises(NotImplementedError):
            session.exists('/path')
        with pytest.raises(NotImplementedError):
            session.put('src_path', 'dest_path')
        with pytest.raises(NotImplementedError):
            session.get('src_path', 'dest_path')
        with pytest.raises(NotImplementedError):
            session.get_mtime('path')
        with pytest.raises(NotImplementedError):
            session.read('path')
        with pytest.raises(NotImplementedError):
            session.mkdir('path')
        with pytest.raises(NotImplementedError):
            session.mktmpdir()
        with pytest.raises(NotImplementedError):
            session.isdir('path')
        with pytest.raises(NotImplementedError):
            session.chmod('path', 'mode')
        with pytest.raises(NotImplementedError):
            session.chown('path', 100)


# Run the abstract method tests for each class the inherits the Session class.
@pytest.fixture(params=[
    DockerSession,
    PTYDockerSession,
    ShellSession,
    SingularitySession,
    PTYSingularitySession,
    SSHSession,
    PTYSSHSession
])
def resource_session(request):
    """Pytest fixture that provides instantiated session objects for each
    of the classes that inherit the Session or POSIXSession classes.

    The fixture will run the test method once for each session object provided.

    Parameters
    ----------
    request : object
        Pytest request object that contains the class to test against

    Yields
    -------
    session object
        Instantiated object based on a class that extends the Session or
        POSIXSession class
    """
    # Initialize docker connection to testing container.
    if request.param in [DockerSession, PTYDockerSession]:
        client = docker.Client()
        container = [
            c for c in client.containers()
            if '/testing-container' in c['Names']
        ][0]
        yield request.param(client, container)
    elif request.param in [SSHSession, PTYSSHSession]:
        # Initialize SSH connection to testing Docker container.
        connection = Connection(
            'localhost',
            user='root',
            port=49000,
            connect_kwargs={
                'password': 'root'
            }
        )
        connection.open()
        yield request.param(connection)
    elif request.param in [SingularitySession, PTYSingularitySession]:
        # Initialize Singularity test container.
        name = str(uuid.uuid4().hex)[:11]
        resource = Singularity(name=name, image='docker://python:2.7')
        resource.connect()
        resource.create()
        yield request.param(name)
        resource.delete()
    else:
        yield request.param()



def test_session_abstract_methods(testing_container, resource_session,
        resource_test_dir):

    session = resource_session

    # Check the validity of the env vars
    envs = session.query_envvars()
    assert 'HOME' in envs
    assert 'PATH' in envs

    # Check sourcing new env variables
    # new_envs = session.source_script(['export', 'SCRIPT_VAR=SCRIPT_VALUE'])
    # assert 'SCRIPT_VAR' in new_envs

    # Check _execute_command by checking file system
    out, err = session._execute_command(['cat', '/etc/hosts'])
    assert '127.0.0.1' in out
    assert 'localhost' in out
    assert err == ''

    # Check _execute_command failure
    with pytest.raises(CommandError):
        session._execute_command(['cat', '/no/such/file'])

    # Check _execute_command with env set
    # TODO: Implement env parameter for _execute_command()
    if session.__class__.__name__ != 'ShellSession':
        with pytest.raises(NotImplementedError):
            out, err = session._execute_command(['cat', '/etc/hosts'],
                env={'NEW_VAR': 'NEW_VAR_VALUE'})

    # Check _execute_command with cwd set
    # TODO: Implement cwd parameter for _execute_command()
    if 'DockerSession' in session.__class__.__name__:
        with swallow_logs(new_level=logging.WARN) as log:
            session._execute_command(['cat', '/etc/hosts'], cwd='/tmp')
            assert "cwd is not handled in docker yet" in log.out
    elif session.__class__.__name__ != 'ShellSession':
        with pytest.raises(NotImplementedError):
            out, err = session._execute_command(['cat', '/etc/hosts'],
                cwd='/tmp')

    # Check exists() method
    result = session.exists('/etc')
    assert result
    result = session.exists('/etc/hosts')
    assert result
    result = session.exists('/no/such/file')
    assert not result
    # exists() doesn't get confused by an empty string.
    assert not session.exists('')

    # Check isdir() method
    result = session.isdir('/etc')
    assert result
    result = session.isdir('/etc/hosts')  # A file, not a dir
    assert not result
    result = session.isdir('/no/such/dir')
    assert not result

    # Create a temporary test file
    temp_file = tempfile.NamedTemporaryFile(dir=resource_test_dir)
    with temp_file as f:
        f.write('NICEMAN test content\nline 2\nline 3'.encode('utf8'))
        f.flush()
        local_path = temp_file.name
        remote_path = '{}/niceman upload/{}'.format(resource_test_dir,
            uuid.uuid4().hex)

        # Check put() method
        # session.put(local_path, remote_path, uid=3, gid=3) # UID for sys, GID for sys
        # TODO: Sort out permissions issues with chown for SSH when no sudo
        session.put(local_path, remote_path)
        result = session.exists(remote_path)
        assert result
        # TODO: Check uid and gid of remote file

        # We can use a relative name for the target
        basename_put_dir = os.path.join(resource_test_dir, "basename-put")
        if not os.path.exists(basename_put_dir):
            os.mkdir(basename_put_dir)
        # Change directory to avoid polluting test directory for local shell.
        with chpwd(basename_put_dir):
            try:
                session.put(local_path, os.path.basename(remote_path))
            except ValueError:
                # Docker and Singularity don't accept non-absolute paths.
                assert isinstance(session, (DockerSession, SingularitySession))

    # Check get_mtime() method by checking new file has today's date
    result = int(session.get_mtime(remote_path).split('.')[0])
    assert datetime.datetime.fromtimestamp(result).month == \
        datetime.date.today().month
    assert datetime.datetime.fromtimestamp(result).day == \
        datetime.date.today().day

    # Check read() method
    output = session.read(remote_path).split('\n')
    assert output[0] == 'NICEMAN test content'
    assert output[1] == 'line 2'

    # Check get() method
    local_path = '{}/download/{}'.format(resource_test_dir,
        uuid.uuid4().hex)
    session.get(remote_path, local_path)
    # TODO: In some cases, updating uid and gid does not work if not root
    assert os.path.isfile(local_path)
    with open(local_path, 'r') as f:
        content = f.read().split('\n')
        assert content[0] == 'NICEMAN test content'
    os.remove(local_path)
    os.rmdir(os.path.dirname(local_path))

    with chpwd(resource_test_dir):
        # We can get() without a leading directory.
        session.get(remote_path, "just base")
        assert os.path.exists("just base")
        remote_basename = os.path.basename(remote_path)
        # We can get() without specifying a target.
        session.get(remote_path)
        assert os.path.exists(remote_basename)
        # Or by specifying just the directory.
        session.get(remote_path, "subdir" + os.path.sep)
        assert os.path.exists(os.path.join("subdir", remote_basename))

    # Check mkdir() method
    test_dir = '{}/{}'.format(resource_test_dir, uuid.uuid4().hex)
    session.mkdir(test_dir)
    result = session.isdir(test_dir)
    assert result

    # Check making parent dirs without setting flag
    test_dir = '{}/tmp/i fail/{}'.format(resource_test_dir, uuid.uuid4().hex)
    with pytest.raises(CommandError):
        session.mkdir(test_dir, parents=False)
    result = session.isdir(test_dir)
    assert not result
    # Check making parent dirs when parents flag set
    test_dir = '{}/i succeed/{}'.format(resource_test_dir, uuid.uuid4().hex)
    session.mkdir(test_dir, parents=True)
    result = session.isdir(test_dir)
    assert result

    # Check mktmpdir() method
    test_dir = session.mktmpdir()
    result = session.isdir(test_dir)
    assert result, "The path %s is not a directory" % test_dir

    # All sessions will take the command in string form...
    output_string = "{}/stringtest {}".format(
        resource_test_dir, session.__class__.__name__)
    assert not session.exists(output_string)
    session.execute_command("touch '{}'".format(output_string))
    assert session.exists(output_string)
    # and the list form.
    output_list = "{}/listtest {}".format(
        resource_test_dir, session.__class__.__name__)
    assert not session.exists(output_list)
    session.execute_command(["touch", output_list])
    assert session.exists(output_list)

    # TODO: How to test chmod and chown? Need to be able to read remote file attributes
    # session.chmod(self, path, mode, recursive=False):
    # session.chown(self, path, uid=-1, gid=-1, recursive=False, remote=True):
