# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from niceman.cmdline.main import main

import logging
from mock import patch, call, MagicMock

from niceman.utils import swallow_logs
from niceman.resource.base import ResourceManager
from niceman.tests.utils import assert_in


def test_login_interface():
    """
    Test logging into an environment
    """

    with patch('docker.Client') as client, \
        patch('niceman.resource.ResourceManager._get_inventory') as get_inventory, \
        patch('dockerpty.start'), \
        swallow_logs(new_level=logging.DEBUG) as log:

        client.return_value = MagicMock(
            containers=lambda all: [
                {
                    'Id': '18b31b30e3a5',
                    'Names': ['/my-test-resource'],
                    'State': 'running'
                }
            ],
        )

        get_inventory.return_value = {
            "my-test-resource": {
                "status": "running",
                "engine_url": "tcp://127.0.0.1:2375",
                "type": "docker-container",
                "name": "my-test-resource",
                "id": "18b31b30e3a5"
            }
        }

        args = ['login',
                'my-test-resource'
        ]

        with patch("niceman.interface.login.get_manager",
                   return_value=ResourceManager()):
            main(args)

        assert client.call_count == 1

        calls = [
            call(base_url='tcp://127.0.0.1:2375')
        ]
        client.assert_has_calls(calls, any_order=True)

        assert_in("Opening TTY connection to docker container.", log.lines)
