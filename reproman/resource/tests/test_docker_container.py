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
from ...tests.utils import assert_in, skip_if_no_docker_engine
from ..base import ResourceManager
from ...support.exceptions import ResourceError
from ...consts import TEST_SSH_DOCKER_DIGEST
from ..docker_container import DockerContainer

from niceman.tests.fixtures import get_docker_fixture

from pytest import raises


setup_ubuntu = get_docker_fixture(
    TEST_SSH_DOCKER_DIGEST,
    scope='module',
    name='niceman-test-ssh-container'
)


def test_dockercontainer_class():

    with patch('docker.Client') as client, \
        patch('dockerpty.start') as dockerpty, \
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
                b'{ "status" : "status 1", "progress" : "progress 1" }',
                b'{ "status" : "status 2", "progress" : "progress 2" }'
            ],
            create_container=lambda name, image, stdin_open, tty, command: {
                'Id': '18b31b30e3a5'
            },
            exec_inspect=lambda id: { 'ExitCode': 0 },
            exec_start=lambda exec_id, stream: [
                b'stdout line 1',
                b'stdout line 2',
                b'stdout line 3'
            ]
        )

        # Test connecting when a resource doens't exist.
        config = {
            'name': 'non-existent-resource',
            'type': 'docker-container'
        }
        resource = ResourceManager.factory(config)
        resource.connect()
        assert resource.id is None
        assert resource.status is None

        # Test catching exception when multiple resources are found at connection.
        config = {
            'name': 'duplicate-resource-name',
            'type': 'docker-container'
        }
        resource = ResourceManager.factory(config)
        with raises(ResourceError) as ecm:
            resource.connect()
        assert ecm.value.args[0].startswith("Multiple container matches found")

        # Test connecting to an existing resource.
        config = {
            'name': 'existing-test-resource',
            'type': 'docker-container',
            'engine_url': 'tcp://127.0.0.1:2375',
            'seccomp_unconfined': True
        }
        resource = ResourceManager.factory(config)
        resource.connect()
        assert resource.image == 'ubuntu:latest'
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
        resource = ResourceManager.factory(config)
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

        # Test logging into the container.
        with resource.get_session(pty=True):
            pass # we do nothing really
        assert dockerpty.called

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


def test_setup_ubuntu(setup_ubuntu):
    assert setup_ubuntu['container_id']


@skip_if_no_docker_engine
def test_engine_exits():
    assert DockerContainer.is_engine_running()
    assert not DockerContainer.is_engine_running(base_url='foo')


@skip_if_no_docker_engine
def test_container_exists(setup_ubuntu):
    assert DockerContainer.is_container_running(setup_ubuntu['name'])
    assert not DockerContainer.is_container_running('foo')
