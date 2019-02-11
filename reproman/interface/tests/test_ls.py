# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from mock import patch

from ...resource.base import ResourceManager
from ...cmdline.main import main
from ...utils import swallow_logs
from ...tests.utils import assert_in

import logging


def mock_get_manager():
    manager = ResourceManager()
    manager.inventory = {
        'docker-resource-1': {
            'status': 'running',
            'engine_url': 'tcp://127.0.0.1:2375',
            'type': 'docker-container',
            'name': 'docker-resource-1',
            'id': '326b0fdfbf838'
        },
        'ec2-resource-1': {
            'id': 'i-22221ddf096c22bb0',
            'type': 'aws-ec2',
            'access_key_id': 'my-aws-access-key-id',
            'secret_access_key': 'my-aws-secret-access-key-id',
            'key_name': 'my-ssh-key',
            'key_filename': '/home/me/.ssh/id_rsa',
            'status': 'running',
            'name': 'ec2-resource-1'
        },
        'ec2-resource-2': {
            'id': 'i-3333f40de2b9b8967',
            'type': 'aws-ec2',
            'access_key_id': 'my-aws-access-key-id',
            'secret_access_key': 'my-aws-secret-access-key-id',
            'key_name': 'my-ssh-key',
            'key_filename': '/home/me/.ssh/id_rsa',
            'status': 'stopped',
            'name': 'ec2-resource-2'
        }
    }
    manager.save_inventory = lambda: None  # Don't save test data to file system.
    return manager


def test_ls_interface():
    """
    Test listing the resources.
    """

    with patch('docker.Client'), \
            patch('reproman.interface.ls.get_manager', new=mock_get_manager), \
            swallow_logs(new_level=logging.DEBUG) as log:

        main(['ls'])
        assert_in('list result: docker-resource-1, docker-container, 326b0fdfbf838, running', log.lines)
        assert_in('list result: ec2-resource-1, aws-ec2, i-22221ddf096c22bb0, running', log.lines)
        assert_in('list result: ec2-resource-2, aws-ec2, i-3333f40de2b9b8967, stopped', log.lines)

        # Test --refresh output
        main(['ls', '--refresh'])
        assert_in('list result: docker-resource-1, docker-container, 326b0fdfbf838, NOT FOUND', log.lines)
        assert_in('list result: ec2-resource-1, aws-ec2, i-22221ddf096c22bb0, CONNECTION ERROR', log.lines)
        assert_in('list result: ec2-resource-2, aws-ec2, i-3333f40de2b9b8967, CONNECTION ERROR', log.lines)
