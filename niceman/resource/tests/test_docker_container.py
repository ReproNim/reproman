# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
from mock import patch, MagicMock, call

from ...utils import swallow_logs
from ...tests.utils import assert_in
from ..base import Resource

def test_dockercontainer_class():

    with patch('docker.Client') as client, \
        swallow_logs(new_level=logging.DEBUG) as log:

        client.return_value = MagicMock(
            containers=lambda all: [
                {
                    'Id': '326b0fdfbf83',
                    'Names': ['/existing-test-resource'],
                    'State': 'running'
                },
                {
                    'Id': '111111111111',
                    'Names': ['/duplicate-resource-name'],
                    'State': 'running'
                },
                {
                    'Id': '222222222222',
                    'Names': ['/duplicate-resource-name'],
                    'State': 'running'
                }
            ],
            pull=lambda repository, stream: [
                '{ "status" : "status 1", "progress" : "progress 1" }',
                '{ "status" : "status 2", "progress" : "progress 2" }'
            ],
            create_container=lambda name, image, stdin_open, detach: {
                'Id': '18b31b30e3a5'
            }
        )

        # Test connecting when a resource doens't exist.
        config = {
            'name': 'non-existent-resource',
            'type': 'docker-container',
        }
        resource = Resource.factory(config)
        resource.connect()
        assert resource.id == None
        assert resource.status == None

        # Test catching exception when multiple resources are found at connection.
        config = {
            'name': 'duplicate-resource-name',
            'type': 'docker-container',
        }
        resource = Resource.factory(config)
        try:
            resource.connect()
        except Exception as e:
            assert e.args[0] == "Multiple container matches found"

        # Test connecting to an existing resource.
        config = {
            'name': 'existing-test-resource',
            'type': 'docker-container',
            'engine_url': 'tcp://127.0.0.1:2375'
        }
        resource = Resource.factory(config)
        resource.connect()
        assert resource.base_image_id == 'ubuntu:latest'
        assert resource.engine_url == 'tcp://127.0.0.1:2375'
        assert resource.id == '326b0fdfbf83'
        assert resource.name == 'existing-test-resource'
        assert resource.status == 'running'
        assert resource.type == 'docker-container'

        # Test creating an existing resource and catch the exception.
        try:
            resource.create()
        except Exception as e:
            assert e.args[0] == "Container 'existing-test-resource' (ID 326b0fdfbf83) already exists in Docker"

        # Test creating resource.
        config = {
            'name': 'new-test-resource',
            'type': 'docker-container',
            'engine_url': 'tcp://127.0.0.1:2375'
        }
        resource = Resource.factory(config)
        resource.connect()
        results = resource.create()
        assert results['id'] == '18b31b30e3a5'
        assert results['status'] == 'running'
        assert_in('status 1 progress 1', log.lines)
        assert_in('status 2 progress 2', log.lines)

        # Test running commands in a resource.
        command = ['apt-get', 'install', 'bc']
        resource.add_command(command)
        command = ['apt-get', 'install', 'xeyes']
        resource.add_command(command)
        resource.execute_command_buffer()
        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['apt-get', 'install', 'xeyes']'", log.lines)

        # Test starting resource.
        resource.start()
        calls = [
            call().start(container='18b31b30e3a5'),
        ]
        client.assert_has_calls(calls, any_order=True)

        # Test stopping resource.
        resource.stop()
        calls = [
            call().stop(container='18b31b30e3a5'),
        ]
        client.assert_has_calls(calls, any_order=True)

        # Test deleting resource.
        resource.delete()
        calls = [
            call().remove_container({'Id': '18b31b30e3a5'}, force=True),
        ]
        client.assert_has_calls(calls, any_order=True)





