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
from repronim.tests.test_constants import DEMO_SPEC1
from repronim.cmd import Runner


def test_install_packages_localhost(tmpdir):
    """
    Test installing packages on the localhost.
    """
    provenance_file = tmpdir.join("demo_spec1.yml")
    provenance_file.write(DEMO_SPEC1)

    with patch.object(Runner, 'run', return_value='installed package') as MockRunner, \
        swallow_logs(new_level=logging.DEBUG) as log:

        args = ['install',
                '--spec', provenance_file.strpath,
                '--platform', 'localhost']
        main(args)

        assert MockRunner.call_count == 8
        calls = [
            call(['apt-get', 'update'], shell=True),
            call(['apt-get', 'install', '-y', 'libc6-dev'], shell=True),
            call(['apt-get', 'install', '-y', 'python-nibabel'], shell=True),
            call(['apt-get', 'install', '-y', 'afni'], shell=True),
            call(['conda', 'install', 'numpy'], shell=True),
        ]
        MockRunner.assert_has_calls(calls, any_order=True)
        assert_in("Adding Debian update to container command list.", log.lines)


def test_install_packages_dockerengine(tmpdir):
    """
    Test installing packages into a Docker container.
    """
    provenance_file = tmpdir.join("demo_spec1.yml")
    provenance_file.write(DEMO_SPEC1)

    with patch('docker.Client') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        # Set up return values for mocked docker.Client methods.
        client = MockClient.return_value
        client.build.return_value = ['{"stream": "Successfully built 9a754690460d\\n"}']
        client.create_container.return_value = {u'Id': u'd4cb4ee', u'Warnings': None}
        client.start.return_value = None
        client.logs.return_value = 'container standard output'

        args = ['install',
                    '--spec', provenance_file.strpath,
                    '--platform', 'dockerengine']
        main(args)

        assert client.build.called
        calls = [call(image=u'9a754690460d', stdin_open=True)]
        client.create_container.assert_has_calls(calls)
        calls = [
            call(cmd=['apt-get', 'update'], container=u'd4cb4ee'),
            call(cmd=['apt-get', 'install', '-y', 'libc6-dev'], container=u'd4cb4ee'),
            call(cmd=['apt-get', 'install', '-y', 'python-nibabel'], container=u'd4cb4ee'),
            call(cmd=['apt-get', 'update'], container=u'd4cb4ee'),
            call(cmd=['apt-get', 'update'], container=u'd4cb4ee'),
            call(cmd=['apt-get', 'install', '-y', 'afni'], container=u'd4cb4ee'),
            call(cmd=['apt-get', 'install', '-y', 'python-nibabel'], container=u'd4cb4ee'),
            call(cmd=['conda', 'install', 'numpy'], container=u'd4cb4ee'),
        ]
        client.exec_create.assert_has_calls(calls, any_order=True)
        assert client.exec_start.call_count == 8
        assert_in("container standard output", log.lines)
        assert_in("Adding Debian update to container command list.", log.lines)