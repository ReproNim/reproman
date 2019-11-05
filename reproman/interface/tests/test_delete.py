# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from reproman.cmdline.main import main

import logging
from unittest.mock import patch, call, MagicMock

from ...resource.base import ResourceManager
from ...utils import swallow_logs
from ...tests.skip import mark
from ...tests.utils import assert_in


def mock_get_manager():
    manager = ResourceManager()
    manager.inventory = {
        "my-resource": {
            "status": "running",
            "engine_url": "tcp://127.0.0.1:2375",
            "type": "docker-container",
            "name": "my-resource",
            "id": "326b0fdfbf838"
        },
        "missing-resource": {
            'id': 'i-22221ddf096c22bb0',
            'type': 'aws-ec2',
            'access_key_id': 'my-aws-access-key-id',
            'secret_access_key': 'my-aws-secret-access-key-id',
            'key_name': 'my-ssh-key',
            'key_filename': '/home/me/.ssh/id_rsa',
            'status': 'running',
            'name': 'missing-resource'
        }
    }
    manager.save_inventory = lambda: None  # Don't save test data to file system.
    return manager


def mock_docker_client():
    mock = MagicMock()
    mock.return_value = MagicMock(
        containers=lambda all: [
            {
                'Id': '326b0fdfbf838',
                'Names': ['/my-resource'],
                'State': 'running'
            }
        ]
    )
    return mock


@mark.skipif_no_docker_dependencies
def test_delete_interface():
    """
    Test deleting a resource.
    """

    with patch('docker.APIClient', new_callable=mock_docker_client) as client, \
            patch('reproman.interface.delete.get_manager',
                new=mock_get_manager), \
            swallow_logs(new_level=logging.DEBUG) as log:

        main(['delete', '--skip-confirmation', 'my-resource'])

        calls = [
            call(base_url='tcp://127.0.0.1:2375'),
            call().remove_container(
                {
                    'State': 'running',
                    'Id': '326b0fdfbf838',
                    'Names': ['/my-resource']
                },
                force=True
            )
        ]
        client.assert_has_calls(calls, any_order=True)
        assert_in('Deleted the environment my-resource', log.lines)
   
        main(['delete', '-y', '--force', 'missing-resource'])
        assert_in('Deleted the environment missing-resource', log.lines)
