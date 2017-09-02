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


def test_delete_interface(niceman_cfg_path):
    """
    Test deleting a resource.
    """

    with patch('docker.Client') as client, \
        patch('niceman.resource.ResourceManager.set_inventory'), \
        patch('niceman.resource.ResourceManager.get_inventory') as get_inventory, \
        swallow_logs(new_level=logging.DEBUG) as log:

        client.return_value = MagicMock(
            containers=lambda all: [
                {
                    'Id': '326b0fdfbf838',
                    'Names': ['/my-resource'],
                    'State': 'running'
                }
            ]
        )

        get_inventory.return_value = {
            "my-resource": {
                "status": "running",
                "engine_url": "tcp://127.0.0.1:2375",
                "type": "docker-container",
                "name": "my-resource",
                "id": "326b0fdfbf838"
            }
        }

        args = [
            'delete',
            '--resource', 'my-resource',
            '--config', niceman_cfg_path,
            '--skip-confirmation'
        ]
        main(args)

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