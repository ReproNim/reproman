# emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Test command call wrapper
"""

from mock import patch
import os
import sys
import logging
import shlex
import pytest

from .utils import ok_, eq_, assert_is, assert_equal, assert_false, \
    assert_true, assert_in

from ..cmd import Runner, link_file_load
from ..support.exceptions import CommandError
from ..support.protocol import DryRunProtocol
from .utils import with_tempfile, assert_cwd_unchanged, \
    swallow_outputs, swallow_logs, \
    on_linux, on_osx, on_windows


@assert_cwd_unchanged
@with_tempfile
def test_runner_dry(tempfile=None):

    dry = DryRunProtocol()
    runner = Runner(protocol=dry)

    # test dry command call
    cmd = 'echo Testing dry run > %s' % tempfile
    with swallow_logs(new_level=logging.DEBUG) as cml:
        ret = runner.run(cmd)
        assert_equal(cml.out.rstrip(), "{DryRunProtocol} Running: %s" % cmd)
    assert_equal(("DRY", "DRY"), ret,
                 "Output of dry run (%s): %s" % (cmd, ret))
    assert_equal(shlex.split(cmd, posix=not on_windows), dry[0]['command'])
    assert_false(os.path.exists(tempfile))

    # test dry python function call
    output = runner.call(os.path.join, 'foo', 'bar')
    assert_is(None, output, "Dry call of: os.path.join, 'foo', 'bar' "
                            "returned: %s" % output)
    assert_in('join', dry[1]['command'][0])
    assert_equal("args=('foo', 'bar')", dry[1]['command'][1])


@assert_cwd_unchanged
@with_tempfile
def test_runner(tempfile=None):

    # test non-dry command call
    runner = Runner()
    cmd = 'echo Testing real run > %s' % tempfile
    ret = runner.run(cmd)
    assert_true(os.path.exists(tempfile),
                "Run of: %s resulted with non-existing file %s" %
                (cmd, tempfile))

    # test non-dry python function call
    output = runner.call(os.path.join, 'foo', 'bar')
    assert_equal(os.path.join('foo', 'bar'), output,
                 "Call of: os.path.join, 'foo', 'bar' returned %s" % output)


def test_runner_instance_callable_dry():

    cmd_ = ['echo', 'Testing', '__call__', 'with', 'string']
    for cmd in [cmd_, ' '.join(cmd_)]:
        dry = DryRunProtocol()
        runner = Runner(protocol=dry)
        ret = runner(cmd)
        # (stdout, stderr) is returned.  But in dry -- ("DRY","DRY")
        eq_(ret, ("DRY", "DRY"))
        assert_equal(cmd_, dry[0]['command'],
                     "Dry run of Runner.__call__ didn't record command: %s.\n"
                     "Buffer: %s" % (cmd, dry))

    ret = runner(os.path.join, 'foo', 'bar')
    eq_(ret, None)

    assert_in('join', dry[1]['command'][0],
              "Dry run of Runner.__call__ didn't record function join()."
              "Buffer: %s" % dry)
    assert_equal("args=('foo', 'bar')", dry[1]['command'][1],
                 "Dry run of Runner.__call__ didn't record function join()."
                 "Buffer: %s" % dry)


def test_runner_instance_callable_wet():

    runner = Runner()
    cmd = [sys.executable, "-c", "print('Testing')"]

    out = runner(cmd)
    eq_(out[0].rstrip(), ('Testing'))
    eq_(out[1], '')

    ret = runner(os.path.join, 'foo', 'bar')
    eq_(ret, os.path.join('foo', 'bar'))


def test_runner_log_stderr():
    # TODO: no idea of how to check correct logging via any kind of
    # assertion yet.

    runner = Runner()
    cmd = 'echo stderr-Message should be logged >&2'
    ret = runner.run(cmd, log_stderr=True, expect_stderr=True)

    cmd = 'echo stderr-Message should not be logged >&2'
    with swallow_outputs() as cmo:
        with swallow_logs(new_level=logging.INFO) as cml:
            ret = runner.run(cmd, log_stderr=False)
            eq_(cmo.err.rstrip(), "stderr-Message should not be logged")
            eq_(cml.out, "")


def test_runner_log_stdout():
    # TODO: no idea of how to check correct logging via any kind of
    # assertion yet.

    runner = Runner()
    cmd_ = ['echo', 'stdout-Message should be logged']
    for cmd in [cmd_, ' '.join(cmd_)]:
        # should be identical runs, either as a string or as a list
        kw = {}
        # on Windows it can't find echo if ran outside the shell
        if on_windows and isinstance(cmd, list):
            kw['shell'] = True
        with swallow_logs(logging.DEBUG) as cm:
            ret = runner.run(cmd, log_stdout=True, **kw)
            eq_(cm.lines[0], "Running: %s" % cmd)
            if not on_windows:
                # we can just count on sanity
                eq_(cm.lines[1], "stdout| stdout-"
                                 "Message should be logged")
            else:
                # echo outputs quoted lines for some reason, so relax check
                ok_("stdout-Message should be logged" in cm.lines[1])

    cmd = 'echo stdout-Message should not be logged'
    with swallow_outputs() as cmo:
        with swallow_logs(new_level=logging.INFO) as cml:
            ret = runner.run(cmd, log_stdout=False)
            eq_(cmo.out, "stdout-Message should not be logged\n")
            eq_(cml.out, "")


@with_tempfile
def test_link_file_load(tempfile=None):
    tempfile2 = tempfile + '_'

    with open(tempfile, 'w') as f:
        f.write("LOAD")

    link_file_load(tempfile, tempfile2)  # this should work in general

    ok_(os.path.exists(tempfile2))

    with open(tempfile2, 'r') as f:
        assert_equal(f.read(), "LOAD")

    def inode(fname):
        with open(fname) as fd:
            return os.fstat(fd.fileno()).st_ino

    def stats(fname, times=True):
        """Return stats on the file which should have been preserved"""
        with open(fname) as fd:
            st = os.fstat(fd.fileno())
            stats = (st.st_mode, st.st_uid, st.st_gid, st.st_size)
            if times:
                return stats + (st.st_atime, st.st_mtime)
            else:
                return stats
            # despite copystat mtime is not copied. TODO
            #        st.st_mtime)

    if on_linux or on_osx:
        # above call should result in the hardlink
        assert_equal(inode(tempfile), inode(tempfile2))
        assert_equal(stats(tempfile), stats(tempfile2))

        # and if we mock absence of .link
        def raise_AttributeError(*args):
            raise AttributeError("TEST")

        with patch('os.link', raise_AttributeError):
            with swallow_logs(logging.WARNING) as cm:
                link_file_load(tempfile, tempfile2)  # should still work
                ok_("failed (TEST), copying file" in cm.out)

    # should be a copy (either originally for windows, or after mocked call)
    ok_(inode(tempfile) != inode(tempfile2))
    with open(tempfile2, 'r') as f:
        assert_equal(f.read(), "LOAD")
    assert_equal(stats(tempfile, times=False), stats(tempfile2, times=False))
    os.unlink(tempfile2)  # TODO: next two with_tempfile


@with_tempfile(mkdir=True)
def test_runner_failure(dir_=None):
    runner = Runner()
    failing_cmd = ['sh', '-c', 'exit 2']

    with swallow_logs() as cml:
        with pytest.raises(CommandError) as cme:
            runner.run(failing_cmd, cwd=dir_)
        assert_in('Failed to run', cml.out)
        assert_equal(2, cme.value.code)
