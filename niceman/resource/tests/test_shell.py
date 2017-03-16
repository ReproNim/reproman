# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
from mock import patch, call

from ...utils import swallow_logs
from ...tests.utils import assert_in
from ..base import Resource
from ...cmd import Runner


def test_shell_class():

    with patch.object(Runner, 'run', return_value='installed package') as runner, \
            swallow_logs(new_level=logging.DEBUG) as log:

        # Test running some install commands.
        config = {
            'name': 'my-shell',
            'type': 'shell'
        }
        shell = Resource.factory(config)

        command = ['apt-get', 'install', 'bc']
        shell.add_command(command)
        command = ['apt-get', 'install', 'xeyes']
        shell.add_command(command)
        shell.execute_command_buffer()
        calls = [
            call(['apt-get', 'install', 'xeyes']),
            call(['apt-get', 'install', 'bc']),
        ]
        runner.assert_has_calls(calls, any_order=True)
        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['apt-get', 'install', 'xeyes']'", log.lines)
