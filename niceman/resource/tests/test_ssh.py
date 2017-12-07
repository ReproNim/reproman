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
from ...tests.utils import assert_in, skip_if_no_network
from ..base import ResourceManager
from ...support.starcluster.sshutils import SSHClient
from ..cmd import Runner


@skip_if_no_network
def test_ssh_class():

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
