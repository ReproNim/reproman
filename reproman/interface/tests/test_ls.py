# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import contextlib
from io import StringIO
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
    stream = StringIO()

    def fn(*args, **kwargs):
        skipif.no_docker_dependencies()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch("docker.Client"))
            stack.enter_context(patch("reproman.interface.ls.get_manager",
                                      return_value=resource_manager))
            stack.enter_context(patch("reproman.interface.ls.ui._ui.out",
                                      stream))
            return ls(*args, **kwargs), stream.getvalue()
    return fn


def test_ls_interface(ls_fn):
    """
    Test listing the resources.
    """
    table, _ = ls_fn()
    dr1 = table[("docker-resource-1",)]
    assert dr1["status"] == "running"
    assert dr1["type"] == "docker-container"
    assert table[("ec2-resource-1",)]["id"] == "i-22221ddf096c22bb0"
    er2 = table[("ec2-resource-2",)]
    assert er2["status"] == "stopped"
    assert er2["type"] == "aws-ec2"

    # Test --refresh output
    table, _ = ls_fn(refresh=True)
    assert table[("docker-resource-1",)]["status"] == "NOT FOUND"
    assert table[("ec2-resource-1",)]["status"] == "CONNECTION ERROR"
    assert table[("ec2-resource-2",)]["status"] == "CONNECTION ERROR"


def test_ls_interface_limited(ls_fn):
    _, stdout = ls_fn(resrefs=["326", "i-33"])
    assert "326b0fdfbf838" in stdout
    assert "i-22221ddf096c22bb0" not in stdout
    assert "i-3333f40de2b9b8967" in stdout
