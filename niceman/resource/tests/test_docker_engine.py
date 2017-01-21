# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ..base import ResourceConfig, Resource

import logging
from mock import patch, call

from niceman.utils import swallow_logs
from niceman.tests.utils import assert_in


def test_dockerengine_class(niceman_cfg_path):

    with patch('docker.DockerClient') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        resource_config = ResourceConfig('remote-docker',
                                         config_path=niceman_cfg_path)
        Resource.factory(resource_config)

        calls = [
            call('tcp://127.0.0.1:2375')
        ]
        MockClient.assert_has_calls(calls, any_order=True)

        assert_in('Getting item "resource_type" in resource config "remote-docker"', log.lines)
        assert_in('Getting item "engine_url" in resource config "remote-docker"', log.lines)

        # Test setting the default engine url if not provided.
        del resource_config['engine_url']
        Resource.factory(resource_config)
        assert resource_config['engine_url'] == 'unix:///var/run/docker.sock'

