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
from ..localshellenvironment import LocalshellEnvironment
from ...cmd import Runner


def test_localshellenvironment_class():

    config = {
        'resource_id': 'my-localshell-env'
    }

    with patch.object(Runner, 'run', return_value='installed package') as MockRunner, \
            swallow_logs(new_level=logging.DEBUG) as log:

        # Test running some install commands.
        env = LocalshellEnvironment(config)
        command = ['apt-get', 'install', 'bc']
        env.add_command(command)
        command = ['apt-get', 'install', 'xeyes']
        env.add_command(command)
        env.execute_command_buffer()
        calls = [
            call(['apt-get', 'install', 'xeyes']),
            call(['apt-get', 'install', 'bc']),
        ]
        MockRunner.assert_has_calls(calls, any_order=True)
        assert_in("Running command '['apt-get', 'install', 'bc']'", log.lines)
        assert_in("Running command '['apt-get', 'install', 'xeyes']'", log.lines)
