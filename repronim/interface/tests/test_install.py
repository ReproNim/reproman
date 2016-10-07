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
  - name: "bash"
    version: "4.2-2ubuntu2.6"
    size: 1449984
    packfiles: true
    files:
      # Total files used: 936.64 KB
      # Installed package size: 1.38 MB
      - "/bin/bash" # 936.64 KB
"""

@with_tree(tree={'sample.yml': REPROZIP_OUTPUT})
def test_install_packages(path):
    """Test installing 2 packages on the localhost.
    """
    testfile = pathjoin(path, 'sample.yml')
    with patch.object(Runner, 'run', return_value='installed package') as mocked_call, \
        swallow_logs(new_level=logging.DEBUG) as log:

        main(['install', '--spec', testfile, '--platform', 'localhost'])

        calls = [call(['apt-get', 'install', '-y', package], shell=True) for package in ('base-files', 'bash')]
        mocked_call.assert_has_calls(calls)

        assert_in("Installing package: base-files", log.lines)
        assert_in("Installing package: bash", log.lines)
        assert_in("installed package", log.lines)