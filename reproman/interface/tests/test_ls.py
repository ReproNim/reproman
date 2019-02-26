# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from mock import patch

from ...api import ls
from ...resource.base import ResourceManager


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
            patch('reproman.interface.ls.get_manager', new=mock_get_manager):
        results = ls()
        assert "running" in results["326b0fdfbf838"]
        assert "docker-container" in results["326b0fdfbf838"]
        assert "i-22221ddf096c22bb0" in results
        assert "stopped" in results["i-3333f40de2b9b8967"]
        assert "aws-ec2" in results["i-3333f40de2b9b8967"]

        # Test --refresh output
        results = ls(refresh=True)
        assert "NOT FOUND" in results["326b0fdfbf838"]
        assert "CONNECTION ERROR" in results["i-22221ddf096c22bb0"]
        assert "CONNECTION ERROR" in results["i-3333f40de2b9b8967"]
