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
from repronim.tests.test_constants import REPROZIP_OUTPUT
from repronim.cmd import Runner


def test_install_packages_localhost(tmpdir):
    """Test installing 2 packages on the localhost.
    """
    provenance_file = tmpdir.join("reprozip.yml")
    provenance_file.write(REPROZIP_OUTPUT)

    with patch.object(Runner, 'run', return_value='installed package') as mocked_call, \
        swallow_logs(new_level=logging.DEBUG) as log:

        main(['install', '--spec', provenance_file.strpath, '--platform', 'localhost'])

        calls = [call(['apt-get', 'install', '-y', package], shell=True)
                 for package in ('base-files', 'bc')]
        mocked_call.assert_has_calls(calls)

        assert_in("Installing package: base-files", log.lines)
        assert_in("Installing package: bc", log.lines)
        assert_in("installed package", log.lines)


def test_install_packages_dockerengine(tmpdir):
    """Test installing 2 packages into a Docker container.
    """
    provenance_file = tmpdir.join("reprozip.yml")
    provenance_file.write(REPROZIP_OUTPUT)

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
                    '--platform', 'dockerengine',
                    #'--host', 'tcp://127.0.0.1:2375',
                    #'--image', 'repronim_test'
                ]
        main(args)

        assert client.build.called
        assert client.create_container.called
        assert client.start.called
        calls = [call(environment={'MATH_EXPRESSION': '2+2', 'TERM': 'xterm'},
                      image=None,
                      name=None
                      #image='repronim_test',
                      #name='repronim_test'
                    )]
        client.create_container.assert_has_calls(calls)
        assert_in("container standard output", log.lines)