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
import os
import paramiko
import pytest
import uuid

from ..session import get_updated_env, Session, POSIXSession
from ...support.exceptions import CommandError
from ..docker_container import DockerSession, PTYDockerSession
from ..shell import ShellSession
from ..ssh import SSHSession, PTYSSHSession
from ...tests.utils import skip_ssh
from ...tests.fixtures import get_docker_fixture


# Note: due to skip_ssh right here, it would skip the entire module with
# all the tests here if no ssh testing is requested
docker_container = skip_ssh(get_docker_fixture)(
    'rastasheep/ubuntu-sshd:14.04',
    name='testing-container',
    portmaps={
        49000: 22
    },
    custom_params={
            'host': 'localhost',
            'user': 'root',
            'password': 'root',
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
    # get_local_session(env={'LC_ALL': 'C'}, pty=False, shared=False)
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
    
    Returns
    -------
    session object
        Instantiated object based on a class that extends the Session or
        POSIXSession class
    """
    # Initialize docker connection to testing container.
    if request.param in [DockerSession, PTYDockerSession]:
        client = docker.Client()
        container = [c for c in client.containers()
            if '/testing-container' in c['Names']][0]
        return request.param(client, container)

    # Initialize SSH connection to testing Docker container.
    if request.param in [SSHSession, PTYSSHSession]:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            'localhost',
            port=49000,
            username='root',
            password='root'
        )
        return request.param(ssh)

    return request.param() 


def test_session_abstract_methods(docker_container, resource_session,
    temp_file, resource_test_dir):

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
    if session.__class__.__name__ != 'ShellSession':
        with pytest.raises(NotImplementedError):
            out, err = session._execute_command(['cat', '/etc/hosts'],
                cwd='/tmp')

    # Check exists() method
    result = session.exists('/etc')
    assert result == True
    result = session.exists('/etc/hosts')
    assert result == True
    result = session.exists('/no/such/file')
    assert result == False

    # Check isdir() method
    result = session.isdir('/etc')
    assert result == True
    result = session.isdir('/etc/hosts') # A file, not a dir
    assert result == False
    result = session.isdir('/no/such/dir')
    assert result == False

    # Write content to the temp_file
    temp_file("""NICEMAN test content
line 2
line 3
""")
    local_path = temp_file.path
    remote_path = '{}/niceman-upload/{}'.format(resource_test_dir,
        uuid.uuid4().hex)

    # Check put() method
    # session.put(local_path, remote_path, uid=3, gid=3) # UID for sys, GID for sys
    # TODO: Sort out permissions issues with chown for SSH when no sudo
    session.put(local_path, remote_path) # UID for sys, GID for sys
    result = session.exists(remote_path)
    assert result == True
    # TODO: Check uid and gid of remote file

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
    assert os.path.isfile(local_path) == True
    with open(local_path, 'r') as f:
        content = f.read().split('\n')
        assert content[0] == 'NICEMAN test content'
    os.remove(local_path)
    os.rmdir(os.path.dirname(local_path))

    # Check mkdir() method
    test_dir = '{}/{}'.format(resource_test_dir, uuid.uuid4().hex)
    session.mkdir(test_dir)
    result = session.isdir(test_dir)
    assert result == True
    # Check making parent dirs without setting flag
    test_dir = '/tmp/failed/{}'.format(resource_test_dir, uuid.uuid4().hex)
    with pytest.raises(CommandError):
        session.mkdir(test_dir, parents=False)
    result = session.isdir(test_dir)
    assert result == False
    # Check making parent dirs when parents flag set
    test_dir = '{}/success/{}'.format(resource_test_dir, uuid.uuid4().hex)
    session.mkdir(test_dir, parents=True)
    result = session.isdir(test_dir)
    assert result == True

    # TODO: How to test chmod and chown? Need to be able to read remote file attributes
    # session.chmod(self, path, mode, recursive=False):
    # session.chown(self, path, uid=-1, gid=-1, recursive=False, remote=True):
