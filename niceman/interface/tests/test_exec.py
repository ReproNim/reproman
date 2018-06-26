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
import logging
from mock import patch

from niceman.utils import swallow_logs, swallow_outputs
from ...resource.base import ResourceManager
from ...tests.utils import skip_ssh
from ...tests.utils import assert_raises
from ...tests.fixtures import get_docker_fixture


docker_container = skip_ssh(get_docker_fixture)(
    'rastasheep/ubuntu-sshd:14.04',
    name='testing-container',
    scope='module'
)

def test_exec_interface(niceman_cfg_path, docker_container):

    with patch('niceman.resource.ResourceManager.set_inventory'), \
        patch('niceman.resource.ResourceManager.get_inventory') as get_inventory, \
        swallow_logs(new_level=logging.DEBUG) as cml:

        config = {
            "status": "running",
            "engine_url": "unix:///var/run/docker.sock",
            "type": "docker-container",
            "name": "testing-container",
        }

        path = '/tmp/{}'.format(str(uuid.uuid4()))

        get_inventory.return_value = {
            "testing-container": config
        }

        cmd = ['exec', 'mkdir', path, '--name', 'testing-container',
                 '--config', niceman_cfg_path]
        main(cmd)

        session = ResourceManager.factory(config).get_session()

        assert session.exists(path)

        # on 2nd run mkdir should fail since already exists
        with swallow_outputs() as cmo:
            with assert_raises(SystemExit) as cme:
                main(cmd)
            assert cme.exception.code == 1
            assert "File exists" in cmo.err
