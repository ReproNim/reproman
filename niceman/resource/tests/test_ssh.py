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
from ...tests.utils import assert_in
from ..base import ResourceManager

import pytest
from nose import SkipTest
import subprocess

@pytest.fixture
def setup_docker():
    """pytest fixture for tests needing a running docker container

    on setup, this fixture ensures that a docker container that maps 
    host port 49000 to container port 22 is running and starts one if necessary

    on teardown, this fixture stops the docker container if it was started by 
    the fixture
    """
    po = subprocess.Popen(['docker', 'ps'], stdout=subprocess.PIPE)
    stdout = po.communicate()[0]
    po.wait()
    # stdout is a bytes object in Python 3, so we need to make the 
    # search string a bytes object as well
    if b'0.0.0.0:49000->22/tcp' in stdout:
        stop_container = False
    else:
        args = ['docker', 
                'run', 
                '-d', 
                '-p', 
                '49000:22', 
                'rastasheep/ubuntu-sshd:14.04']
        po = subprocess.Popen(args, stdout=subprocess.PIPE)
        stdout = po.communicate()[0]
        returncode = po.wait()
        assert returncode == 0, 'error starting docker container'
        container_id = stdout.strip()
        stop_container = True
    yield
    if stop_container:
        subprocess.check_call(['docker', 'stop', container_id])
    return

def test_ssh_class(setup_docker):

    if os.environ.get('NICEMAN_TESTS_NONETWORK'):
        raise SkipTest("Skipping since no network settings")

    with swallow_logs(new_level=logging.DEBUG) as log:

        # Test connecting to test SSH server.
        # TODO: Add a test using a SSH key pair.
        config = {
            'name': 'ssh-test-resource',
            'type': 'ssh',
            'host': 'localhost',
            'user': 'root',
            'password': 'root',
            'port': '49000'
        }
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
