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
from mock import patch, call, MagicMock

from ...utils import swallow_logs
from ...tests.utils import assert_in


def test_install_interface(demo1_spec, niceman_cfg_path):

    with patch('docker.Client') as client, \
        patch('niceman.resource.ResourceManager.set_inventory'), \
        patch('niceman.resource.ResourceManager.get_inventory') as get_inventory, \
        swallow_logs(new_level=logging.DEBUG) as log:

        client.return_value = MagicMock(
            containers=lambda all: [
                {
                    'Id': '326b0fdfbf838',
                    'Names': ['/my-resource'],
                    'State': 'running'
                }
            ]
        )

        get_inventory.return_value = {
            "my-resource": {
                "status": "running",
                "engine_url": "tcp://127.0.0.1:2375",
                "type": "docker-container",
                "name": "my-resource",
                "id": "326b0fdfbf838"
            }
        }

        args = ['install',
                '--spec', demo1_spec,
                '--name', 'my-resource',
                '--config', niceman_cfg_path
        ]
        main(args)

        def container_call(cmd):
            return call().exec_create(
                cmd=cmd,
                container={'State': 'running', 'Id': '326b0fdfbf838', 'Names': ['/my-resource']}
            )
        calls = [
            call(base_url='tcp://127.0.0.1:2375'),
            container_call(['apt-get', 'update']),
            # call().exec_create(cmd=['apt-get', 'install', '-y', 'python-pip'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
            # call().exec_create(cmd=['apt-get', 'install', '-y', 'libc6-dev'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
            # call().exec_create(cmd=['apt-get', 'install', '-y', 'python-nibabel'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
            # call().exec_create(cmd=['apt-get', 'update'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
            # call().exec_create(cmd=['apt-get', 'install', '-y', 'python-pip'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
            # call().exec_create(cmd=['apt-get', 'update'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
            # call().exec_create(cmd=['apt-get', 'install', '-y', 'python-pip'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
            container_call(
                ['apt-get', 'install', '-y', 'libc6-dev=2.19-18+deb8u4', 'afni=16.2.07~dfsg.1-2~nd90+1']
            ),
            # call().exec_create(cmd=['apt-get', 'install', '-y', 'python-nibabel'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
            # call().exec_create(cmd=['pip', 'install', 'piponlypkg'],
            #     container={'State': 'running', 'Id': '326b0fdfbf83', 'Names': ['/my-resource']}),
        ]
        client.assert_has_calls(calls, any_order=True)

        assert_in("Adding Debian update to environment command list.", log.lines)
        assert_in("Running command ['apt-get', 'update']", log.lines)
        # assert_in("Running command '['apt-get', 'install', '-y', 'python-pip']'", log.lines)
        # assert_in("Running command '['apt-get', 'install', '-y', 'libc6-dev']'", log.lines)
        # assert_in("Running command '['apt-get', 'install', '-y', 'python-nibabel']'", log.lines)
        # assert_in("Running command '['apt-get', 'install', '-y', 'afni']'", log.lines)
        # assert_in("Running command '['pip', 'install', 'piponlypkg']'", log.lines)