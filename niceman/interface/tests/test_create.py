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
from niceman.tests.utils import assert_in

import niceman.tests.fixtures

def test_create_interface(niceman_cfg_path):
    """
    Test creating an environment
    """

    with patch('docker.Client') as client, \
        patch('niceman.interface.base.set_resource_inventory'), \
        patch('niceman.interface.base.get_resource_inventory') as get_inventory, \
        swallow_logs(new_level=logging.DEBUG) as log:

        client.return_value = MagicMock(
            containers=lambda all: [],
            pull=lambda repository, tag, stream: [
                '{ "status" : "status 1", "progress" : "progress 1" }',
                '{ "status" : "status 2", "progress" : "progress 2" }'
            ],
            create_container=lambda name, image, stdin_open, detach: {
                'Id': '18b31b30e3a5'
            }
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

        args = ['create',
                '--resource', 'my-test-resource',
                '--resource-type', 'docker-container',
                '--config', niceman_cfg_path
        ]
        main(args)

        calls = [
            call(base_url='tcp://127.0.0.1:2375'),
            call().start(container='18b31b30e3a5')
        ]
        client.assert_has_calls(calls, any_order=True)

        assert_in("status 1 progress 1", log.lines)
        assert_in("status 2 progress 2", log.lines)
        assert_in("Created the environment my-test-resource", log.lines)