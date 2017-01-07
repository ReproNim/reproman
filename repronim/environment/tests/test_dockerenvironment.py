# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
from mock import patch, call

from ...utils import swallow_logs
from ...tests.utils import assert_in
from ..dockerenvironment import DockerEnvironment

def test_dockerenvironment_class():

    config = {
        'resource_id': 'my-docker-env',
        'resource_type': 'docker-environment',
        'resource_client': 'remote-docker-engine',
        'config_path': '/path/to/config/file',
    }

    with patch('docker.DockerClient') as MockDockerClient, \
        patch('repronim.resource.Resource.factory') as MockResourceClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        # Test initializing the environment object.
        env = DockerEnvironment(config)
        calls = [
            call('remote-docker-engine', config_path='/path/to/config/file')
        ]
        MockResourceClient.assert_has_calls(calls, any_order=True)

        # Test creating an environment.
        name = 'my-test-environment'
        image_id = 'ubuntu:trusty'
        env.create(name, image_id)
        assert env['name'] == 'my-test-environment'
        assert env['base_image_id'] == 'ubuntu:trusty'

        # Test connecting to an environment and running some install commands.
        env = DockerEnvironment(config)
        env.connect(name)
        command = ['apt-get', 'install', 'bc']
        env.add_command(command)
        command = ['apt-get', 'install', 'xeyes']
        env.add_command(command)
        env.execute_command_buffer()
        calls = [
            call()().containers.get('my-test-environment'),
            call()().containers.get().exec_run(
                cmd=['apt-get', 'install', 'bc'], stream=True),
            call()().containers.get().exec_run(
                cmd=['apt-get', 'install', 'xeyes'], stream=True),
        ]
        MockResourceClient.assert_has_calls(calls, any_order=True)
        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['apt-get', 'install', 'xeyes']'", log.lines)

        # Test removing the container and image.
        env.remove_container()
        env.remove_image()
        calls = [
            call.remove(force=True)
        ]
        env._container.assert_has_calls(calls, any_order=True)
