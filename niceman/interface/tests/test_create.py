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
from niceman.cmd import Runner

import niceman.tests.fixtures


# def test_install_packages_localhost(demo1_spec, niceman_cfg_path):
#     """
#     Test installing packages on the localhost.
#     """
#     with patch.object(Runner, 'run', return_value='installed package') as MockRunner, \
#         patch('os.environ.copy') as MockOS, \
#         swallow_logs(new_level=logging.DEBUG) as log:
#
#         MockOS.return_value = {}
#
#         args = ['install',
#                 '--spec', demo1_spec,
#                 '--resource', 'localhost-shell',
#                 '--config', niceman_cfg_path,
#                 ]
#         main(args)
#
#         assert MockRunner.call_count == 9
#         calls = [
#             call(['apt-get', 'update']),
#             call(['apt-get', 'install', '-y', 'libc6-dev'], env={'DEBIAN_FRONTEND': 'noninteractive'}),
#             call(['apt-get', 'install', '-y', 'python-nibabel'], env={'DEBIAN_FRONTEND': 'noninteractive'}),
#             call(['apt-get', 'install', '-y', 'afni'], env={'DEBIAN_FRONTEND': 'noninteractive'}),
#             # call(['conda', 'install', 'numpy'], env={'DEBIAN_FRONTEND': 'noninteractive'}),
#         ]
#         MockRunner.assert_has_calls(calls, any_order=True)
#         assert_in("Adding Debian update to container command list.", log.lines)


def test_install_packages_dockerengine(demo1_spec, niceman_cfg_path):
    """
    Test installing packages into a Docker container.
    """

    with patch('docker.Client') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        args = ['create',
                    '--spec', demo1_spec,
                    '--resource', 'my-debian',
                    '--config', niceman_cfg_path
                ]
        main(args)

        calls = [
            call(base_url='tcp://127.0.0.1:2375'),
        ]
        MockClient.assert_has_calls(calls, any_order=True)

        assert_in("Created the environment my-debian", log.lines)