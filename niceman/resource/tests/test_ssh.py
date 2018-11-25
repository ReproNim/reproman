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
import pytest
import re
import six
import uuid
from pytest import raises

from ...utils import swallow_logs
from ...tests.utils import assert_in, skip_ssh
from ..base import ResourceManager
from niceman.tests.fixtures import get_docker_fixture
from ...consts import TEST_SSH_DOCKER_DIGEST

# Note: due to skip_ssh right here, it would skip the entire module with
# all the tests here if no ssh testing is requested
setup_ssh = skip_ssh(get_docker_fixture)(
    TEST_SSH_DOCKER_DIGEST,
    portmaps={
        49000: 22
    },
    custom_params={
        'host': 'localhost',
        'user': 'root',
        'port': 49000
    },
    scope='module'
)


def test_setup_ssh(setup_ssh):
    # Rudimentary smoke test for setup_ssh so we have
    # multiple uses for the setup_ssh
    assert 'port' in setup_ssh['custom']
    assert setup_ssh['custom']['host'] == 'localhost'


def test_ssh_class(setup_ssh, resource_test_dir):
    with swallow_logs(new_level=logging.DEBUG) as log:

        # Test connecting to test SSH server.
        # TODO: Add a test using a SSH key pair.
        config = dict(
            name='ssh-test-resource',
            type='ssh',
            **setup_ssh['custom']
        )
        resource = ResourceManager.factory(config)
        updated_config = resource.create()
        config.update(updated_config)
        assert re.match('\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$',
                        resource.id) is not None
        assert resource.status == 'N/A'

        # Test running commands in a resource.
        resource.connect(password='root')
        command = ['apt-get', 'install', '-y', 'bc']
        resource.add_command(command)
        command = ['ls', '/']
        resource.add_command(command)
        resource.execute_command_buffer()
        assert_in("Running command '['apt-get', 'install', '-y', 'bc']'", log.lines)
        assert_in("Running command '['ls', '/']'", log.lines)
        # TODO: Figure out why PY3 logger is not picking up STDOUT from SSH server.
        if six.PY2:
            assert_in("Running command '['apt-get', 'install', '-y', 'bc']'", log.lines)
            assert_in("Running command '['ls', '/']'", log.lines)

        # Test SSHSession methods
        session = resource.get_session()

        assert session.exists('/etc/hosts')
        assert session.exists('/no/such/file') is False

        # Copy this file to /root/test_ssh.py on the docker test container.
        session.put(__file__, 'remote_test_ssh.py')
        assert session.exists('remote_test_ssh.py')

        tmp_path = "{}/{}".format(resource_test_dir, uuid.uuid4().hex)
        session.get('/etc/hosts', tmp_path)
        assert os.path.isfile(tmp_path)

        file_contents = session.read('remote_test_ssh.py')
        file_contents = file_contents.splitlines()
        assert file_contents[8] == '# Test string to read'

        path = '/tmp/{}'.format(str(uuid.uuid4()))
        assert session.isdir(path) is False
        session.mkdir(path)
        assert session.isdir(path)

        path = '/tmp/{}/{}'.format(str(uuid.uuid4()), str(uuid.uuid4()))
        assert session.isdir(path) is False
        session.mkdir(path, parents=True)
        assert session.isdir(path)

        assert not session.isdir('not-a-dir')
        assert not session.isdir('/etc/hosts')

        with raises(NotImplementedError):
            session._execute_command('non-existent-command', cwd='/path')


def test_ssh_resource(setup_ssh):

    config = {
        'name': 'ssh-test-resource',
        'type': 'ssh',
        'host': 'localhost',
        'user': 'root',
        'port': 49000
    }
    resource = ResourceManager.factory(config)
    resource.connect(password='root')

    with pytest.raises(NotImplementedError):
        resource.start()
    with pytest.raises(NotImplementedError):
        resource.stop()

    resource.delete()
    assert resource._connection is None

    # resource.get_session()
    # assert type(resource._transport) == paramiko.Transport
