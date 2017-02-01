# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
from mock import patch, call

from ...utils import swallow_logs
from ...tests.utils import assert_in
from ..base import ResourceConfig, Resource

def test_dockercontainer_class(niceman_cfg_path):

    with patch('docker.DockerClient') as MockDockerClient, \
        swallow_logs(new_level=logging.DEBUG) as log:

        # Test initializing the environment object.
        resource_config = ResourceConfig('my-debian',
                                         config_path=niceman_cfg_path)
        docker_container = Resource.factory(resource_config)

        # Test creating an environment.
        name = 'my-test-environment'
        image_id = 'ubuntu:trusty'
        docker_container.create(name, image_id)
        assert docker_container.get_config('name') == 'my-test-environment'
        assert docker_container.get_config('base_image_id') == 'ubuntu:trusty'

        # Test connecting to an environment and running some install commands.
        docker_container.connect(name)
        command = ['apt-get', 'install', 'bc']
        docker_container.add_command(command)
        command = ['apt-get', 'install', 'xeyes']
        docker_container.add_command(command)
        docker_container.execute_command_buffer()
        calls = [
            call().containers.get('my-test-environment')
        ]
        MockDockerClient.assert_has_calls(calls, any_order=True)
        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['apt-get', 'install', 'xeyes']'", log.lines)

        # Test removing the container and image.
        docker_container.remove_container()
        docker_container.remove_image()
        calls = [
            call.remove(force=True)
        ]
        docker_container._container.assert_has_calls(calls, any_order=True)
