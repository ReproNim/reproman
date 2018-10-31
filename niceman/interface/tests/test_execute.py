# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from niceman.cmdline.main import main

import uuid
from mock import patch
import pytest

from niceman.api import execute
from niceman.utils import swallow_outputs
from ...resource.base import ResourceManager
from ...tests.utils import skip_ssh
from ...tests.fixtures import get_docker_fixture
from ...consts import TEST_SSH_DOCKER_DIGEST


docker_container = skip_ssh(get_docker_fixture)(
    TEST_SSH_DOCKER_DIGEST,
    name='testing-container',
    scope='module'
)


def test_execute_interface(docker_container):

    with patch('niceman.resource.ResourceManager._get_inventory') as get_inventory:
        config = {
            "status": "running",
            "engine_url": "unix:///var/run/docker.sock",
            "type": "docker-container",
            "name": "testing-container",
        }

        get_inventory.return_value = {
            "testing-container": config
        }

        for internal in [False, True]:
            path = '/tmp/{}'.format(str(uuid.uuid4()))
            cmd = ['execute', '--resource', 'testing-container']
            if internal:
                cmd.append('--internal')
            cmd.extend(['mkdir', path])

            manager = ResourceManager()
            with patch("niceman.interface.execute.get_manager",
                       return_value=manager):
                main(cmd)

                session = manager.get_resource("testing-container").get_session()
                assert session.exists(path)

                # on 2nd run mkdir should fail since already exists
                with swallow_outputs() as cmo:
                    with pytest.raises(SystemExit) as cme:
                        main(cmd)
                    assert cme.value.code == 1
                    assert "File exists" in cmo.err


def test_invalid_trace_internal():
    with pytest.raises(RuntimeError):
        execute("doesn't matter", [], internal=True, trace=True)
