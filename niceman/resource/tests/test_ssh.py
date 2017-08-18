# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
from mock import patch, call, MagicMock

from ...utils import swallow_logs
from ...tests.utils import assert_in
from ..base import ResourceManager


def test_ssh_class():

    with patch('niceman.support.sshconnector2.SSHConnector2'), \
        swallow_logs(new_level=logging.DEBUG) as log:

        # Test connecting when a resource doesn't exist.
        config = {
            'name': 'non-existent-ssh',
            'type': 'ssh',
            'host': 'www.not-a-real-server.com',
            'user': 'ubuntu',
            'key_filename': '/home/ubuntu/.ssh/id_rsa',
        }
        resource = ResourceManager.factory(config)
        updated_config = resource.create()
        config.update(updated_config)
        assert resource.id == 'www.not-a-real-server.com'
        assert resource.status == 'N/A'

        # Test running commands in a resource.
        resource.connect()
        command = ['apt-get', 'install', 'bc']
        resource.add_command(command)
        command = ['apt-get', 'install', 'xeyes']
        resource.add_command(command)
        resource.execute_command_buffer()
        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['apt-get', 'install', 'xeyes']'", log.lines)
