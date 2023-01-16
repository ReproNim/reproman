# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Test invocation of reproman utilities "as is installed"
"""

from unittest.mock import patch

import pytest
from .utils import ok_startswith, eq_, \
    assert_cwd_unchanged

from reproman.cmd import Runner
from reproman.support.exceptions import CommandError

def check_run_and_get_output(cmd):
    runner = Runner()
    try:
        # suppress log output happen it was set to high values
        with patch.dict('os.environ', {'REPROMAN_LOGLEVEL': 'WARN'}):
            output = runner.run(["reproman", "--help"])
    except CommandError as e:
        raise AssertionError("'reproman --help' failed to start normally. "
                             "Exited with %d and output %s" % (e.code, (e.stdout, e.stderr)))
    return output


@assert_cwd_unchanged
def test_run_reproman_help():
    out, err = check_run_and_get_output("reproman --help")
    ok_startswith(out, "Usage: ")
    if "OpenSSL version 1.0.1 is no longer supported" in err:
        # Running the test on Travis currently has a warning.
        # https://travis-ci.org/ReproNim/reproman/jobs/499326699#L2162
        pytest.xfail(reason="err not empty due to OpenSSL warning")
    eq_(err, "")
