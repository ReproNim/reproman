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
#             call(['apt-get', 'install', '-y', 'libc6-dev']),
#             call(['apt-get', 'install', '-y', 'python-nibabel']),
#             call(['apt-get', 'install', '-y', 'afni']),
#             # call(['conda', 'install', 'numpy']),
#         ]
#         MockRunner.assert_has_calls(calls, any_order=True)
#         assert_in("Adding Debian update to container command list.", log.lines)


def test_install_packages_dockerengine(demo1_spec, niceman_cfg_path):

    with patch('docker.DockerClient') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        args = ['install',
                    '--spec', demo1_spec,
                    '--resource', 'my-debian',
                    '--config', niceman_cfg_path
                ]
        main(args)

        calls = [
            call('tcp://127.0.0.1:2375'),
            call().containers.get('my-great-docker-container'),
            call().containers.get().exec_run(cmd=['apt-get', 'update'],
                                             stream=True),
            call().containers.get().exec_run(
                cmd=['apt-get', 'install', '-y', 'python-pip'], stream=True),
            call().containers.get().exec_run(
                cmd=['apt-get', 'install', '-y', 'libc6-dev'], stream=True),
            call().containers.get().exec_run(
                cmd=['apt-get', 'install', '-y', 'python-nibabel'], stream=True),
            call().containers.get().exec_run(cmd=['apt-get', 'update'],
                                             stream=True),
            call().containers.get().exec_run(
                cmd=['apt-get', 'install', '-y', 'python-pip'], stream=True),
            call().containers.get().exec_run(cmd=['apt-get', 'update'],
                                             stream=True),
            call().containers.get().exec_run(
                cmd=['apt-get', 'install', '-y', 'python-pip'], stream=True),
            call().containers.get().exec_run(
                cmd=['apt-get', 'install', '-y', 'afni'], stream=True),
            call().containers.get().exec_run(
                cmd=['apt-get', 'install', '-y', 'python-nibabel'], stream=True),
            call().containers.get().exec_run(cmd=['pip', 'install', 'piponlypkg'],
                                             stream=True),
        ]
        MockClient.assert_has_calls(calls, any_order=True)

        assert_in("Adding Debian update to environment command list.", log.lines)
        assert_in("Running command '['apt-get', 'update']'", log.lines)
        assert_in(
            "Running command '['apt-get', 'install', '-y', 'python-pip']'", log.lines)
        assert_in(
            "Running command '['apt-get', 'install', '-y', 'libc6-dev']'", log.lines)
        assert_in(
            "Running command '['apt-get', 'install', '-y', 'python-nibabel']'", log.lines)
        assert_in(
            "Running command '['apt-get', 'install', '-y', 'afni']'", log.lines)
        assert_in(
            "Running command '['pip', 'install', 'piponlypkg']'", log.lines)