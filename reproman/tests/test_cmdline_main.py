# emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Test functioning of the niceman main cmdline utility """

import re
import sys
from six.moves import StringIO
from mock import patch
import pytest

import niceman
from ..cmdline.main import main
from .utils import assert_equal, in_, ok_startswith


def run_main(args, exit_code=0, expect_stderr=False):
    """Run main() of the niceman, do basic checks and provide outputs

    Parameters
    ----------
    args : list
        List of string cmdline arguments to pass
    exit_code : int
        Expected exit code. Would raise AssertionError if differs
    expect_stderr : bool or string
        Either to expect stderr output. If string -- match

    Returns
    -------
    stdout, stderr  strings
       Output produced
    """
    with patch('sys.stderr', new_callable=StringIO) as cmerr:
        with patch('sys.stdout', new_callable=StringIO) as cmout:
            with pytest.raises(SystemExit) as cm:
                main(args)
            assert_equal(cm.value.code, exit_code)  # exit code must be 0
            stdout = cmout.getvalue()
            stderr = cmerr.getvalue()
            if expect_stderr == False:
                assert_equal(stderr, "")
            elif expect_stderr == True:
                # do nothing -- just return
                pass
            else:
                # must be a string
                assert_equal(stderr, expect_stderr)
    return stdout, stderr


# TODO: switch to stdout for --version output
def test_version():
    stdout, stderr = run_main(['--version'], expect_stderr=True)

    # and output should contain our version, copyright, license

    # https://hg.python.org/cpython/file/default/Doc/whatsnew/3.4.rst#l1952
    out = stdout if sys.version_info >= (3, 4) else stderr
    ok_startswith(out, 'niceman %s\n' % niceman.__version__)
    in_("Copyright", out)
    in_("Permission is hereby granted", out)


def test_help_np():
    stdout, stderr = run_main(['--help-np'])

    # Let's extract section titles:
    # enough of bin/niceman and .tox/py27/bin/niceman -- guarantee consistency! ;)
    ok_startswith(stdout, 'Usage: niceman')
    # Sections start/end with * if ran under NICEMAN_HELP2MAN mode
    sections = [l[1:-1] for l in filter(re.compile('^\*.*\*$').match, stdout.split('\n'))]
    # but order is still not guaranteed (dict somewhere)! TODO
    # see https://travis-ci.org/niceman/niceman/jobs/80519004
    # thus testing sets
    assert_equal(set(sections),
                 {'Commands for manipulating computation environments',
                  'Miscellaneous commands',
                  'General information',
                  'Global options'})

# MJT - This test incorrectly tests how the create, ls, install, etc. commands
# work as they now prompt for missing args rather than display a usage message.
# def test_usage_on_insufficient_args():
#     stdout, stderr = run_main(['create'], exit_code=1)
#     ok_startswith(stdout, 'usage:')
