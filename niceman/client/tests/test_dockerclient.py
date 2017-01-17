# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ..dockerclient import DockerClient

import logging
from mock import patch, call

from niceman.utils import swallow_logs
from niceman.tests.utils import assert_in


def test_dockerclient_class():

    # Test connecting to a mock docker server.
    config = {
        'resource_id': 'my-docker-client',
        'engine_url': 'tcp://127.0.0.1:2375'
    }

    with patch('docker.DockerClient') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        MockClient.return_value = 'connection made to docker'

        DockerClient(config)

        calls = [
            call('tcp://127.0.0.1:2375')
        ]
        MockClient.assert_has_calls(calls, any_order=True)

    # Test setting the default engine url if not provided.
    config = {
        'resource_id': 'my-docker-client'
    }
    client = DockerClient(config)
    assert client['engine_url'] == 'unix:///var/run/docker.sock'

