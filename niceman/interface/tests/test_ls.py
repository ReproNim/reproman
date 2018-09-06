# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from mock import patch, MagicMock

from ...cmdline.main import main
from ...utils import swallow_logs
from ...resource.base import ResourceManager
from ...tests.utils import assert_in

import logging


def test_ls_interface():
    """
    Test listing the resources.
    """

    with patch('docker.Client') as docker_client, \
        patch('boto3.resource') as aws_client, \
        patch('niceman.resource.ResourceManager._get_inventory') as get_inventory, \
        swallow_logs(new_level=logging.DEBUG) as log:

        docker_client.return_value = MagicMock(
            containers=lambda all: [
                {
                    'Id': '326b0fdfbf83',
                    'Names': ['/my-resource'],
                    'State': 'running'
                }
            ]
        )

        aws_client.side_effect = [
            MagicMock(Instance=lambda id: MagicMock(
                instance_id='i-22221ddf096c22bb0',
                state={'Name': 'running'}
            )),
            MagicMock(Instance=lambda id: MagicMock(
                instance_id='i-3333f40de2b9b8967',
                state={'Name': 'stopped'}
            )),
        ]

        get_inventory.return_value = {
            "docker-resource-1": {
                "status": "running",
                "engine_url": "tcp://127.0.0.1:2375",
                "type": "docker-container",
                "name": "my-resource",
                "id": "326b0fdfbf838"
            },
            "ec2-resource-1": {
                'id': 'i-22221ddf096c22bb0',
                'type': 'aws-ec2',
                'access_key_id': 'my-aws-access-key-id',
                'secret_access_key': 'my-aws-secret-access-key-id',
                'key_name': 'my-ssh-key',
                'key_filename': '/home/me/.ssh/id_rsa',
                "status": "running",
                "name": "aws-resource-1"
            },
            "ec2-resource-2": {
                'id': 'i-3333f40de2b9b8967',
                'type': 'aws-ec2',
                'access_key_id': 'my-aws-access-key-id',
                'secret_access_key': 'my-aws-secret-access-key-id',
                'key_name': 'my-ssh-key',
                'key_filename': '/home/me/.ssh/id_rsa',
                "status": "stopped",
                "name": "aws-resource-2"
            }
        }

        args = [
            'ls',
        ]
        with patch("niceman.interface.login.get_manager",
                   return_value=ResourceManager()):
            main(args)

        assert_in(
            'list result: docker-resource-1, docker-container, 326b0fdfbf838, running',
            log.lines)
        assert_in('list result: ec2-resource-1, aws-ec2, i-22221ddf096c22bb0, running', log.lines)
        assert_in('list result: ec2-resource-2, aws-ec2, i-3333f40de2b9b8967, stopped', log.lines)