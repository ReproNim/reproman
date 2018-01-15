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

from ...utils import swallow_logs
from ...tests.utils import assert_in, skip_if_no_network, skip_ssh
from ..base import ResourceManager
from ...cmd import Runner

import pytest
from nose import SkipTest


def setup_docker(image, portmaps={}, name=None):
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
    params = {
        'host': 'localhost',
        'user': 'root',
        'password': 'root',
    }
    args = ['docker',
            'run',
            '-d',
            '--rm',
            ]
    if name:
        args += ['--name', name]
        params['name'] = name

    if portmaps:
        for from_to in portmaps.items():
            args += ['-p', '%d:%d' % from_to]
            params['port'] = from_to[0]
    args += [image]

    stdout, _ = Runner().run(args)
    container_id = stdout.strip()
    yield params
    Runner().run(['docker', 'stop', container_id])
    return


@pytest.fixture(scope='module')
def setup_ssh():
    for i in setup_docker(
        image='rastasheep/ubuntu-sshd:14.04',
        portmaps={
            49000: 22
        }
    ):
        yield i


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

        session.mkdir('test-dir')
        assert session.isdir('test-dir') == True
        assert session.isdir('not-a-dir') == False
        assert session.isdir('/etc/hosts') == False
