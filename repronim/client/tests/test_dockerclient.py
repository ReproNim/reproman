# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ..dockerclient import DockerClient

import logging
from mock import patch, call

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in


def test_dockerclient_class():

    # Test connecting to a mock docker server.
    config = {
        'engine_url': 'tcp://127.0.0.1:2375'
    }
    env = DockerClient(config)

    with patch('docker.DockerClient') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        MockClient.return_value = 'connection made to docker'

        env.connect()

        calls = [
            call('tcp://127.0.0.1:2375')
        ]
        MockClient.assert_has_calls(calls, any_order=True)

        assert env.get_connection() == 'connection made to docker'
        assert_in('Connected to docker at tcp://127.0.0.1:2375', log.lines)

    # Test setting the default engine url if not provided.
    config = {}
    env = DockerClient(config)
    assert env.get_config('engine_url') == 'unix:///var/run/docker.sock'

