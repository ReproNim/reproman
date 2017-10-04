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
from ...tests.utils import assert_in, skip_if_no_network
from ..base import ResourceManager


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

        session.copy_to(__file__)
        assert session.exists('test_ssh.py') == True

        tmp_path = "/tmp/{}".format(uuid.uuid4().hex)
        # session.copy_from('test_ssh.py', tmp_path)
        # assert os.path.isfile(tmp_path) == True

        # file_contents = session.read('test_ssh.py')
        # assert file_contents[8] == '# Test string to read\n'

        session.mkdir('test-dir')
        assert session.isdir('test-dir') == True
        assert session.isdir('not-a-dir') == False
