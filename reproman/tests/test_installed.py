# emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Test invocation of niceman utilities "as is installed"
"""

from mock import patch
from .utils import ok_startswith, eq_, \
    assert_cwd_unchanged

from niceman.cmd import Runner
from niceman.support.exceptions import CommandError

def check_run_and_get_output(cmd):
    runner = Runner()
    try:
        # suppress log output happen it was set to high values
        with patch.dict('os.environ', {'NICEMAN_LOGLEVEL': 'WARN'}):
            output = runner.run(["niceman", "--help"])
    except CommandError as e:
        raise AssertionError("'niceman --help' failed to start normally. "
                             "Exited with %d and output %s" % (e.code, (e.stdout, e.stderr)))
    return output


@assert_cwd_unchanged
def test_run_niceman_help():
    out, err = check_run_and_get_output("niceman --help")
    ok_startswith(out, "Usage: ")
    eq_(err, "")