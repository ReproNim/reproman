# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
# Test string to read

import logging
import os
import re
import six
import uuid
from pytest import raises

from ...utils import swallow_logs
from ...tests.utils import assert_in, skip_if_no_network, skip_ssh
from ..base import ResourceManager
from ...support.starcluster.sshutils import SSHClient

import pytest
from nose import SkipTest

@pytest.fixture(scope='module')
def setup_ssh():
    """pytest fixture for tests needing a running docker container

    on setup, this fixture ensures that a docker container that maps 
    host port 49000 to container port 22 is running and starts one if necessary.

    Fixture yields parameters of the ssh connection suitable to be used as is
    for ssh type resource.

    on teardown, this fixture stops the docker container if it was started by 
    the fixture
    """

    skip_if_no_network()
    skip_ssh()
    stdout, _ = Runner().run(['docker', 'ps'])
    params = {
        'host': 'localhost',
        'user': 'root',
        'password': 'root',
        'port': '49000',
    }
    if '0.0.0.0:{port}->22/tcp'.format(**params) in stdout:
        stop_container = False
    else:
        args = ['docker',
                'run',
                '-d',
                '--rm',
                '-p',
                '{port}:22'.format(**params),
                'rastasheep/ubuntu-sshd:14.04']
        stdout, _ = Runner().run(args)
        container_id = stdout.strip()
        stop_container = True
    yield params
    if stop_container:
        Runner().run(['docker', 'stop', container_id])
    return


def test_setup_ssh(setup_ssh):
    # Rudimentary smoke test for setup_ssh so we have
    # multiple uses for the setup_ssh
    assert 'port' in setup_ssh
    assert setup_ssh['host'] == 'localhost'


def test_ssh_class(setup_ssh):
    with swallow_logs(new_level=logging.DEBUG) as log:

        # Test connecting to test SSH server.
        # TODO: Add a test using a SSH key pair.
        config = dict(
            name='ssh-test-resource',
            type='ssh',
            **setup_ssh
        )
        resource = ResourceManager.factory(config)
        updated_config = resource.create()
        config.update(updated_config)
        assert re.match('\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$',
                        resource.id) is not None
        assert resource.status == 'N/A'

        # Test running commands in a resource.
        resource.connect()
        command = ['apt-get', 'install', 'bc']
        resource.add_command(command)
        command = ['ls', '/']
        resource.add_command(command)
        resource.execute_command_buffer()
        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['ls', '/']'", log.lines)
        # TODO: Figure out why PY3 logger is not picking up STDOUT from SSH server.
        if six.PY2:
            assert_in('exec#0: Reading package lists...', log.lines)
            assert_in('exec#0: bin', log.lines)

        # Test SSHSession methods
        session = resource.get_session()

        assert session.exists('/etc/hosts') == True
        assert session.exists('/no/such/file') == False

        # Copy this file to /root/test_ssh.py on the docker test container.
        session.put(__file__, 'remote_test_ssh.py')
        assert session.exists('remote_test_ssh.py') == True

        tmp_path = "/tmp/{}".format(uuid.uuid4().hex)
        session.get('/etc/hosts', tmp_path)
        assert os.path.isfile(tmp_path) == True

        file_contents = session.read('remote_test_ssh.py')
        assert file_contents[8] == '# Test string to read\n'

        path = '/tmp/{}'.format(str(uuid.uuid4()))
        assert session.isdir(path) == False
        session.mkdir(path)
        assert session.isdir(path) == True

        path = '/tmp/{}/{}'.format(str(uuid.uuid4()), str(uuid.uuid4()))
        assert session.isdir(path) == False
        session.mkdir(path, parents=True)
        assert session.isdir(path) == True

        assert session.isdir('not-a-dir') == False
        assert session.isdir('/etc/hosts') == False

        with raises(NotImplementedError) as err:
            session._execute_command('non-existent-command', cwd='/path')


@skip_if_no_network
def test_ssh_resource():

    config = {
        'name': 'ssh-test-resource',
        'type': 'ssh',
        'host': 'localhost',
        'user': 'root',
        'password': 'root',
        'port': '49000'
    }
    resource = ResourceManager.factory(config)
    resource.connect()

    assert resource.start() == None
    assert resource.stop() == None

    resource.delete()
    assert resource._ssh == None

    resource.get_session()
    assert type(resource._ssh) == SSHClient
