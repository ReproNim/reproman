# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
from mock import patch

from ...utils import swallow_logs
from ...tests.utils import assert_in
from ..base import ResourceConfig, Resource

def test_dockercontainer_class(niceman_cfg_path):

    with patch('docker.Client'), \
        swallow_logs(new_level=logging.DEBUG) as log:

        # Test initializing the environment object.
        resource_config = ResourceConfig('my-debian',
                                         config_path=niceman_cfg_path)
        docker_container = Resource.factory(resource_config)

        # Test creating an environment.
        image_id = 'ubuntu:trusty'
        docker_container.create(image_id)
        assert docker_container.get_config('base_image_id') == 'ubuntu:trusty'

        # Test connecting to an environment and running some install commands.
        docker_container.connect()
        command = ['apt-get', 'install', 'bc']
        docker_container.add_command(command)
        command = ['apt-get', 'install', 'xeyes']
        docker_container.add_command(command)
        docker_container.execute_command_buffer()

        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['apt-get', 'install', 'xeyes']'", log.lines)
