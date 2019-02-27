# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import contextlib
from unittest.mock import patch

import pytest

from ...api import ls
from ...resource.base import ResourceManager
from ...tests.skip import skipif


@pytest.fixture(scope="function")
def resource_manager():
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


@pytest.fixture(scope="function")
def ls_fn(resource_manager):
    def fn(*args, **kwargs):
        skipif.no_docker_dependencies()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch("docker.Client"))
            stack.enter_context(patch("reproman.interface.ls.get_manager",
                                      return_value=resource_manager))
            return ls(*args, **kwargs)
    return fn


def test_ls_interface(ls_fn):
    """
    Test listing the resources.
    """
    results = ls_fn()
    assert "running" in results["326b0fdfbf838"]
    assert "docker-container" in results["326b0fdfbf838"]
    assert "i-22221ddf096c22bb0" in results
    assert "stopped" in results["i-3333f40de2b9b8967"]
    assert "aws-ec2" in results["i-3333f40de2b9b8967"]

    # Test --refresh output
    results = ls_fn(refresh=True)
    assert "NOT FOUND" in results["326b0fdfbf838"]
    assert "CONNECTION ERROR" in results["i-22221ddf096c22bb0"]
    assert "CONNECTION ERROR" in results["i-3333f40de2b9b8967"]


def test_ls_interface_limited(ls_fn):
    results = ls_fn(resrefs=["326", "i-33"])
    assert "326b0fdfbf838" in results
    assert "i-22221ddf096c22bb0" not in results
    assert "i-3333f40de2b9b8967" in results
