# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from niceman.cmdline.main import main

import logging
from mock import patch, call

from niceman.utils import swallow_logs
from niceman.tests.utils import assert_in

def test_delete_docker_container(niceman_cfg_path):
    """
    Test deleting a Docker container.
    """

    with patch('docker.DockerClient') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        args = ['delete',
            '--resource', 'my-debian',
            '--config', niceman_cfg_path
        ]
        main(args)

        calls = [
            call('tcp://127.0.0.1:2375'),
            call().containers.get('my-debian'),
            call().containers.get().remove(force=True)
        ]
        MockClient.assert_has_calls(calls, any_order=True)

        assert_in('Deleted the environment my-debian', log.lines)