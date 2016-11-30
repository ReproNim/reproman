# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.cmdline.main import main

import logging
from mock import patch, call

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in
from repronim.cmd import Runner

import repronim.tests.fixtures


def test_install_packages_localhost(demo1_spec, repronim_cfg_path):
    """
    Test installing packages on the localhost.
    """
    with patch.object(Runner, 'run', return_value='installed package') as MockRunner, \
        patch('os.environ.copy') as MockOS, \
        swallow_logs(new_level=logging.DEBUG) as log:

        MockOS.return_value = {}

        args = ['install',
                '--spec', demo1_spec,
                '--resource', 'localhost-shell',
                '--config', repronim_cfg_path,
                ]
        main(args)

        assert MockRunner.call_count == 9
        calls = [
            call(['apt-get', 'update']),
            call(['apt-get', 'install', '-y', 'libc6-dev'], env={'DEBIAN_FRONTEND': 'noninteractive'}),
            call(['apt-get', 'install', '-y', 'python-nibabel'], env={'DEBIAN_FRONTEND': 'noninteractive'}),
            call(['apt-get', 'install', '-y', 'afni'], env={'DEBIAN_FRONTEND': 'noninteractive'}),
            # call(['conda', 'install', 'numpy'], env={'DEBIAN_FRONTEND': 'noninteractive'}),
        ]
        MockRunner.assert_has_calls(calls, any_order=True)
        assert_in("Adding Debian update to container command list.", log.lines)


def test_install_packages_dockerengine(demo1_spec, repronim_cfg_path):
    """
    Test installing packages into a Docker container.
    """

    with patch('docker.Client') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        # Set up return values for mocked docker.Client methods.
        client = MockClient.return_value
        client.build.return_value = ['{"stream": "Successfully built 9a754690460d\\n"}']
        client.create_container.return_value = {u'Id': u'd4cb4ee', u'Warnings': None}
        client.start.return_value = None
        client.logs.return_value = 'container standard output'

        args = ['install',
                    '--spec', demo1_spec,
                    '--resource', 'remote-docker',
                    '--config', repronim_cfg_path,
                ]
        main(args)

        assert client.build.called
        calls = [call(image=u'9a754690460d', stdin_open=True)]
        client.create_container.assert_has_calls(calls)
        calls = [
            call(cmd=['apt-get', 'update'], container=u'd4cb4ee'),
            call(cmd=['DEBIAN_FRONTEND=noninteractive;', 'apt-get', 'install', '-y', 'libc6-dev'], container=u'd4cb4ee'),
            call(cmd=['DEBIAN_FRONTEND=noninteractive;', 'apt-get', 'install', '-y', 'python-nibabel'], container=u'd4cb4ee'),
            call(cmd=['apt-get', 'update'], container=u'd4cb4ee'),
            call(cmd=['apt-get', 'update'], container=u'd4cb4ee'),
            call(cmd=['DEBIAN_FRONTEND=noninteractive;', 'apt-get', 'install', '-y', 'afni'], container=u'd4cb4ee'),
            call(cmd=['DEBIAN_FRONTEND=noninteractive;', 'apt-get', 'install', '-y', 'python-nibabel'], container=u'd4cb4ee'),
            call(cmd=['conda', 'install', 'numpy'], container=u'd4cb4ee'),
        ]
        client.exec_create.assert_has_calls(calls, any_order=True)
        assert client.exec_start.call_count == 9
        assert_in("container standard output", log.lines)
        assert_in("Adding Debian update to container command list.", log.lines)