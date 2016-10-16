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
from os.path import join as pathjoin
from mock import patch, call

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in
from repronim.tests.utils import with_tree
from repronim.cmd import Runner


# Sample output from Reprozip.
REPROZIP_OUTPUT = """
runs:
# Run 0
- architecture: x86_64
  date: 2016-02-22T22:19:01.735754
  argv: [echo, $MATH_EXPRESSION, '|', bc]
  binary: /usr/bin/bc
  distribution: [Ubuntu, '12.04']
  environ: {TERM: xterm, MATH_EXPRESSION: '2+2'}
  exitcode: 0
  gid: 1003
  hostname: nitrcce
  id: run0
  system: [Linux, 3.2.0-98-virtual]
  uid: 1002
  workingdir: /home/rbuccigrossi/simple_workflow
packages:
  - name: "base-files"
    version: "6.5ubuntu6.8"
    size: 429056
    packfiles: true
    files:
      # Total files used: 103.0 bytes
      # Installed package size: 419.00 KB
      - "/etc/debian_version" # 11.0 bytes
      - "/etc/host.conf" # 92.0 bytes
  - name: "bc"
    version: "1.06.95-2ubuntu1"
    size: 1449984
    packfiles: true
    files:
      # Total files used: 936.64 KB
      # Installed package size: 1.38 MB
      - "/bin/bash" # 936.64 KB
"""

@with_tree(tree={'sample.yml': REPROZIP_OUTPUT})
def test_install_packages_localhost(path):
    """Test installing 2 packages on the localhost.
    """
    testfile = pathjoin(path, 'sample.yml')
    with patch.object(Runner, 'run', return_value='installed package') as mocked_call, \
        swallow_logs(new_level=logging.DEBUG) as log:

        main(['install', '--spec', testfile, '--platform', 'localhost'])

        calls = [call(['apt-get', 'install', '-y', package], shell=True) for package in ('base-files', 'bc')]
        mocked_call.assert_has_calls(calls)

        assert_in("Installing package: base-files", log.lines)
        assert_in("Installing package: bc", log.lines)
        assert_in("installed package", log.lines)

@with_tree(tree={'sample.yml': REPROZIP_OUTPUT})
def test_install_packages_dockerengine(path):
    """Test installing 2 packages into a Docker container.
    """
    testfile = pathjoin(path, 'sample.yml')
    with patch('docker.Client') as MockClient, swallow_logs(new_level=logging.DEBUG) as log:

        # Set up return values for mocked docker.Client methods.
        client = MockClient.return_value
        client.build.return_value = ['{"stream": "Successfully built 9a754690460d\\n"}']
        client.create_container.return_value = {u'Id': u'd4cb4ee', u'Warnings': None}
        client.start.return_value = None
        client.logs.return_value = 'container standard output'

        args = ['install',
                    '--spec', testfile,
                    '--platform', 'dockerengine',
                    '--host', 'mock_host',
                    '--image', 'repronim_test']
        main(args)

        assert client.build.called
        assert client.create_container.called
        assert client.start.called
        calls = [call(environment={'MATH_EXPRESSION': '2+2', 'TERM': 'xterm'}, image='repronim_test', \
                      name='repronim_test')]
        client.create_container.assert_has_calls(calls)
        assert_in("container standard output", log.lines)