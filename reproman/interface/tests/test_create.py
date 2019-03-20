# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##


import logging
import pytest
from unittest.mock import patch, call, MagicMock

from reproman.api import create
from reproman.cmdline.main import main
from reproman.utils import swallow_logs
from reproman.resource.base import ResourceManager
from reproman.tests.skip import mark
from reproman.tests.utils import assert_in
from reproman.support.exceptions import ResourceError


@mark.skipif_no_docker_dependencies
def test_create_interface():
    """
    Test creating an environment
    """

    with patch('docker.Client') as client, \
        patch('reproman.resource.ResourceManager.save_inventory'), \
        patch('reproman.resource.ResourceManager._get_inventory'), \
        swallow_logs(new_level=logging.DEBUG) as log:

        client.return_value = MagicMock(
            containers=lambda all: [],
            pull=lambda repository, stream: [
                b'{ "status" : "status 1", "progress" : "progress 1" }',
                b'{ "status" : "status 2", "progress" : "progress 2" }'
            ],
            create_container=lambda name, image, stdin_open, tty, command: {
                'Id': '18b31b30e3a5'
            }
        )

        args = ['create',
                '--resource-type', 'docker-container',
                '--backend', 'engine_url=tcp://127.0.0.1:2376',
                '--',
                'my-test-resource'
        ]
        with patch("reproman.interface.create.get_manager",
                   return_value=ResourceManager()):
            main(args)

        calls = [
            call(base_url='tcp://127.0.0.1:2376'),
            call().start(container='18b31b30e3a5')
        ]
        client.assert_has_calls(calls, any_order=True)

        assert_in("status 1 progress 1", log.lines)
        assert_in("status 2 progress 2", log.lines)
        assert_in("Created the environment my-test-resource", log.lines)


def test_create_missing_required():
    with pytest.raises(ResourceError) as exc:
        # SSH requires host.
        with patch("reproman.interface.create.get_manager",
                   return_value=ResourceManager()):
            create("somessh", "ssh", [])
    assert "host" in str(exc.value)
