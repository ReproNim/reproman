# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import platform
import sys
import os
import random
import logging

try:
    # optional direct dependency we might want to kick out
    import bs4
except ImportError:
    bs4 = None

from glob import glob
from os.path import exists, basename

from six import PY2
from six import text_type
from six.moves.urllib.request import urlopen

from mock import patch
from .utils import assert_in, assert_not_in, assert_true
import pytest

from ..utils import getpwd, chpwd

from .utils import eq_, ok_, assert_false, ok_startswith, nok_startswith, \
    with_tempfile, with_tree, \
    rmtemp, OBSCURE_FILENAMES, get_most_obscure_supported_name, \
    swallow_logs, \
    on_windows, assert_raises, assert_cwd_unchanged, serve_path_via_http, \
    ok_symlink, ok_good_symlink, ok_broken_symlink, \
    assert_is_subset_recur

from .utils import ok_generator
from .utils import assert_re_in
from .utils import skip_if_no_network
from .utils import run_under_dir
from .utils import ok_file_has_content
from .utils import without_http_proxy

#
# Test with_tempfile, especially nested invocations
#

@with_tempfile
def _with_tempfile_decorated_dummy(path):
    return path


def test_with_tempfile_dir_via_env_variable():
    target = os.path.join(os.path.expanduser("~"), "nicemantesttmpdir")
    assert_false(os.path.exists(target), "directory %s already exists." % target)
    with patch.dict('os.environ', {'NICEMAN_TESTS_TEMPDIR': target}):
        filename = _with_tempfile_decorated_dummy()
        ok_startswith(filename, target)


@with_tempfile
@with_tempfile
def test_nested_with_tempfile_basic(f1=None, f2=None):
    ok_(f1 != f2)
    ok_(not os.path.exists(f1))
    ok_(not os.path.exists(f2))


# And the most obscure case to test.

@with_tempfile(prefix="TEST", suffix='big')
@with_tree((('f1.txt', 'load'),))
@with_tempfile(suffix='.cfg')
@with_tempfile(suffix='.cfg.old')
def test_nested_with_tempfile_surrounded(f0=None, tree=None, f1=None, f2=None):
    ok_(f0.endswith('big'), msg="got %s" % f0)
    ok_(os.path.basename(f0).startswith('TEST'), msg="got %s" % f0)
    ok_(os.path.exists(os.path.join(tree, 'f1.txt')))
    ok_(f1 != f2)
    ok_(f1.endswith('.cfg'), msg="got %s" % f1)
    ok_(f2.endswith('.cfg.old'), msg="got %s" % f2)


@with_tempfile(content="testtest")
def test_with_tempfile_content(f=None):
    ok_file_has_content(f, "testtest")


def test_with_tempfile_content_raises_on_mkdir():

    @with_tempfile(content="test", mkdir=True)
    def t():  # pragma: no cover
        raise AssertionError("must not be run")

    with pytest.raises(ValueError):
        # after this commit, it will check when invoking, not when decorating
        t()


def test_with_tempfile_mkdir():
    dnames = []  # just to store the name within the decorated function

    @with_tempfile(mkdir=True)
    def check_mkdir(d1):
        ok_(os.path.exists(d1))
        ok_(os.path.isdir(d1))
        dnames.append(d1)
        eq_(glob(os.path.join(d1, '*')), [])
        # Create a file to assure we can remove later the temporary load
        with open(os.path.join(d1, "test.dat"), "w") as f:
            f.write("TEST LOAD")

    check_mkdir()
    if not os.environ.get('NICEMAN_TESTS_KEEPTEMP'):
        ok_(not os.path.exists(dnames[0]))  # got removed


@with_tempfile()
def test_with_tempfile_default_prefix(d1=None):
    d = basename(d1)
    short = 'niceman_temp_'
    full = short + \
           'test_with_tempfile_default_prefix'
    if on_windows:
        ok_startswith(d, short)
        nok_startswith(d, full)
    else:
        ok_startswith(d, full)


@with_tempfile(prefix="noniceman_")
def test_with_tempfile_specified_prefix(d1=None):
    ok_startswith(basename(d1), 'noniceman_')
    ok_('test_with_tempfile_specified_prefix' not in d1)


def test_get_most_obscure_supported_name():
    n = get_most_obscure_supported_name()
    if platform.system() in ('Linux', 'Darwin'):
        eq_(n, OBSCURE_FILENAMES[1])
    else:
        # ATM no one else is as good
        ok_(n in OBSCURE_FILENAMES[2:])


def test_keeptemp_via_env_variable():

    if os.environ.get('NICEMAN_TESTS_KEEPTEMP'):
        pytest.skip("We have env variable set to preserve tempfiles")

    files = []

    @with_tempfile()
    def check(f):
        open(f, 'w').write("LOAD")
        files.append(f)

    with patch.dict('os.environ', {}):
        check()

    with patch.dict('os.environ', {'NICEMAN_TESTS_KEEPTEMP': '1'}):
        check()

    eq_(len(files), 2)
    ok_(not exists(files[0]), msg="File %s still exists" % files[0])
    ok_(    exists(files[1]), msg="File %s not exists" % files[1])

    rmtemp(files[-1])


@with_tempfile
def test_ok_symlink_helpers(tmpfile=None):

    if on_windows:
        pytest.skip("no sylmlinks on windows")

    assert_raises(AssertionError, ok_symlink, tmpfile)
    assert_raises(AssertionError, ok_good_symlink, tmpfile)
    assert_raises(AssertionError, ok_broken_symlink, tmpfile)

    tmpfile_symlink = tmpfile + '_symlink'
    os.symlink(tmpfile, tmpfile_symlink)  

    # broken symlink
    ok_symlink(tmpfile_symlink)
    ok_broken_symlink(tmpfile_symlink)
    assert_raises(AssertionError, ok_good_symlink, tmpfile_symlink)

    with open(tmpfile, 'w') as tf:
        tf.write('test text')
    
    # tmpfile is still not a symlink here
    assert_raises(AssertionError, ok_symlink, tmpfile)
    assert_raises(AssertionError, ok_good_symlink, tmpfile)
    assert_raises(AssertionError, ok_broken_symlink, tmpfile)

    ok_symlink(tmpfile_symlink)
    ok_good_symlink(tmpfile_symlink)
    assert_raises(AssertionError, ok_broken_symlink, tmpfile_symlink)


def test_ok_startswith():
    ok_startswith('abc', 'abc')
    ok_startswith('abc', 'a')
    ok_startswith('abc', '')
    ok_startswith(' abc', ' ')
    ok_startswith('abc\r\n', 'a')  # no effect from \r\n etc
    assert_raises(AssertionError, ok_startswith, 'abc', 'b')
    assert_raises(AssertionError, ok_startswith, 'abc', 'abcd')


def test_nok_startswith():
    nok_startswith('abc', 'bc')
    nok_startswith('abc', 'c')
    assert_raises(AssertionError, nok_startswith, 'abc', 'a')
    assert_raises(AssertionError, nok_startswith, 'abc', 'abc')

def test_ok_generator():
    def func(a, b=1):
        return a+b
    def gen(a, b=1):
        yield a+b
    # not sure how to determine if xrange is a generator
    if PY2:
        assert_raises(AssertionError, ok_generator, xrange(2))
    assert_raises(AssertionError, ok_generator, range(2))
    assert_raises(AssertionError, ok_generator, gen)
    ok_generator(gen(1))
    assert_raises(AssertionError, ok_generator, func)
    assert_raises(AssertionError, ok_generator, func(1))


@pytest.mark.parametrize("func", [os.chdir, chpwd],
                         ids=["chdir", "chpwd"])
def test_assert_Xwd_unchanged(func):
    orig_cwd = os.getcwd()
    orig_pwd = getpwd()

    @assert_cwd_unchanged
    def do_chdir():
        func(os.pardir)

    with pytest.raises(AssertionError) as cm:
        do_chdir()

    eq_(orig_cwd, os.getcwd(),
        "assert_cwd_unchanged didn't return us back to cwd %s" % orig_cwd)
    eq_(orig_pwd, getpwd(),
        "assert_cwd_unchanged didn't return us back to pwd %s" % orig_pwd)


@pytest.mark.parametrize("func", [os.chdir, chpwd],
                         ids=["chdir", "chpwd"])
def test_assert_Xwd_unchanged_ok_chdir(func):
    # Test that we are not masking out other "more important" exceptions

    orig_cwd = os.getcwd()
    orig_pwd = getpwd()

    @assert_cwd_unchanged(ok_to_chdir=True)
    def do_chdir_value_error():
        func(os.pardir)

    with swallow_logs() as cml:
        do_chdir_value_error()
        eq_(orig_cwd, os.getcwd(),
            "assert_cwd_unchanged didn't return us back to cwd %s" % orig_cwd)
        eq_(orig_pwd, getpwd(),
            "assert_cwd_unchanged didn't return us back to cwd %s" % orig_pwd)
        assert_not_in("Mitigating and changing back", cml.out)


def test_assert_cwd_unchanged_not_masking_exceptions():
    # Test that we are not masking out other "more important" exceptions

    orig_cwd = os.getcwd()

    @assert_cwd_unchanged
    def do_chdir_value_error():
        os.chdir(os.pardir)
        raise ValueError("error exception")

    with swallow_logs(new_level=logging.WARN) as cml:
        with pytest.raises(ValueError) as cm:
            do_chdir_value_error()
        # retrospect exception
        if PY2:
            # could not figure out how to make it legit for PY3
            # but on manual try -- works, and exception traceback is not masked out
            cm.match('error exception')

        eq_(orig_cwd, os.getcwd(),
            "assert_cwd_unchanged didn't return us back to %s" % orig_cwd)
        assert_in("Mitigating and changing back", cml.out)

    # and again but allowing to chdir
    @assert_cwd_unchanged(ok_to_chdir=True)
    def do_chdir_value_error():
        os.chdir(os.pardir)
        raise ValueError("error exception")

    with swallow_logs(new_level=logging.WARN) as cml:
        assert_raises(ValueError, do_chdir_value_error)
        eq_(orig_cwd, os.getcwd(),
            "assert_cwd_unchanged didn't return us back to %s" % orig_cwd)
        assert_not_in("Mitigating and changing back", cml.out)


def _test_fpaths():
    for test_fpath in ['test1.txt',
                       'test_dir/test2.txt',
                       'test_dir/d2/d3/test3.txt',
                       'file with space test4',
                       u'Джэйсон',
                       get_most_obscure_supported_name(),
                      ]:

        yield test_fpath

    # just with the last one check that we did remove proxy setting
    with patch.dict('os.environ', {'http_proxy': 'http://127.0.0.1:9/'}):
        yield test_fpath


@pytest.mark.parametrize("test_fpath", list(_test_fpaths()))
def test_serve_path_via_http(test_fpath, tmpdir): # pragma: no cover
    tmpdir = str(tmpdir)  # Downstream code fails with a py.path.local object.
    # First verify that filesystem layer can encode this filename
    # verify first that we could encode file name in this environment
    try:
        filesysencoding = sys.getfilesystemencoding()
        test_fpath_encoded = test_fpath.encode(filesysencoding)
    except UnicodeEncodeError:
        pytest.skip("Environment doesn't support unicode filenames")
    if test_fpath_encoded.decode(filesysencoding) != test_fpath:
        pytest.skip("Can't convert back/forth using %s encoding"
                    % filesysencoding)

    test_fpath_full = text_type(os.path.join(tmpdir, test_fpath))
    test_fpath_dir = text_type(os.path.dirname(test_fpath_full))

    if not os.path.exists(test_fpath_dir):
        os.makedirs(test_fpath_dir)

    with open(test_fpath_full, 'w') as f:
        test_txt = 'some txt and a randint {}'.format(random.randint(1, 10)) 
        f.write(test_txt)

    @serve_path_via_http(tmpdir)
    def test_path_and_url(path, url):

        # @serve_ should remove http_proxy from the os.environ if was present
        assert_false('http_proxy' in os.environ)
        url = url + os.path.dirname(test_fpath)
        assert_true(urlopen(url))
        u = urlopen(url)
        assert_true(u.getcode() == 200)
        html = u.read()
        soup = bs4.BeautifulSoup(html, "html.parser")
        href_links = [txt.get('href') for txt in soup.find_all('a')]
        assert_true(len(href_links) == 1)

        url = "{}/{}".format(url, href_links[0])
        u = urlopen(url)
        html = u.read().decode()
        assert(test_txt == html)

    if bs4 is None:
        pytest.skip("bs4 is absent")
    test_path_and_url()


def test_without_http_proxy():

    @without_http_proxy
    def check(a, kw=False):
        assert_false('http_proxy' in os.environ)
        assert_false('https_proxy' in os.environ)
        assert_in(kw, [False, 'custom'])

    check(1)

    with patch.dict('os.environ', {'http_proxy': 'http://127.0.0.1:9/'}):
        check(1)
        check(1, "custom")
        with pytest.raises(AssertionError):
            check(1, "wrong")

    with patch.dict('os.environ', {'https_proxy': 'http://127.0.0.1:9/'}):
        check(1)
    with patch.dict('os.environ', {'http_proxy': 'http://127.0.0.1:9/',
                                   'https_proxy': 'http://127.0.0.1:9/'}):
        check(1)


def test_assert_re_in():
    assert_re_in(".*", "")
    assert_re_in(".*", ["any"])

    # should do match not search
    assert_re_in("ab", "abc")
    assert_raises(AssertionError, assert_re_in, "ab", "cab")
    assert_raises(AssertionError, assert_re_in, "ab$", "abc")

    # Sufficient to have one entry matching
    assert_re_in("ab", ["", "abc", "laskdjf"])
    assert_raises(AssertionError, assert_re_in, "ab$", ["ddd", ""])

    # Tuples should be ok too
    assert_re_in("ab", ("", "abc", "laskdjf"))
    assert_raises(AssertionError, assert_re_in, "ab$", ("ddd", ""))

    # shouldn't "match" the empty list
    assert_raises(AssertionError, assert_re_in, "", [])


def test_skip_if_no_network():
    cleaned_env = os.environ.copy()
    cleaned_env.pop('NICEMAN_TESTS_NONETWORK', None)
    # we need to run under cleaned env to make sure we actually test in both conditions
    with patch('os.environ', cleaned_env):
        @skip_if_no_network
        def somefunc(a1):
            return a1
        eq_(somefunc.tags, ['network'])
        with patch.dict('os.environ', {'NICEMAN_TESTS_NONETWORK': '1'}):
            assert_raises(pytest.skip.Exception, somefunc, 1)
        with patch.dict('os.environ', {}):
            eq_(somefunc(1), 1)
        # and now if used as a function, not a decorator
        with patch.dict('os.environ', {'NICEMAN_TESTS_NONETWORK': '1'}):
            assert_raises(pytest.skip.Exception, skip_if_no_network)
        with patch.dict('os.environ', {}):
            eq_(skip_if_no_network(), None)


@assert_cwd_unchanged
@with_tempfile(mkdir=True)
def test_run_under_dir(d=None):
    orig_pwd = getpwd()
    orig_cwd = os.getcwd()

    @run_under_dir(d)
    def f(arg, kwarg=None):
        eq_(arg, 1)
        eq_(kwarg, 2)
        eq_(getpwd(), d)

    f(1, 2)
    eq_(getpwd(), orig_pwd)
    eq_(os.getcwd(), orig_cwd)

    # and if fails
    assert_raises(AssertionError, f, 1, 3)
    eq_(getpwd(), orig_pwd)
    eq_(os.getcwd(), orig_cwd)


def test_assert_is_subset_recur():
    assert_is_subset_recur(1, 1)
    assert_is_subset_recur({}, {'a': 1}, [dict])
    assert_raises(AssertionError, assert_is_subset_recur,
                  {'a': 1}, {'b': 2}, [dict])
    assert_is_subset_recur({'a': {'z': 1}},
                           {'a': {'y': 2, 'z': 1}}, [dict])
    assert_raises(AssertionError, assert_is_subset_recur,
                  {'a': {'y': 2, 'z': 1}},
                  {'a': {'z': 1}}, [dict])
    assert_is_subset_recur({'a': {'z': [1]}},
                           {'a': {'y': 2, 'z': [1]}}, [dict])
    assert_raises(AssertionError, assert_is_subset_recur,
                  {'a': {'y': 2, 'z': [1]}},
                  {'a': {'z': [1]}}, [dict])
    assert_is_subset_recur({'a': {'z': [1]}},
                           {'a': {'z': [1]}}, [])
    assert_raises(AssertionError, assert_is_subset_recur,
                  {'a': {'z': [1]}},
                  {'a': {'y': 2, 'z': [1]}}, [])
    assert_is_subset_recur([1, 2], [3, 2, 1], [list])
    assert_raises(AssertionError, assert_is_subset_recur,
                  [3, 2, 1], [1, 2], [list])
    assert_is_subset_recur([3, [2]], [3, [2, 1]], [list])
    assert_raises(AssertionError, assert_is_subset_recur,
                  [3, [2, 1]], [3, [2]], [list])
    assert_is_subset_recur([3, [2]], [3, [2]], [dict])
    assert_raises(AssertionError, assert_is_subset_recur,
                  [3, [2]], [3, [2, 1]], [dict])


def test_skip_ssh():
    from .utils import skip_ssh

    try:
        @skip_ssh
        def func(x):
            return x + 2

        with patch.dict('os.environ', {'NICEMAN_TESTS_SSH': "1"}):
            assert func(2) == 4
    except pytest.skip.Exception:
        raise AssertionError("must have not skipped")

    with patch.dict('os.environ', {'NICEMAN_TESTS_SSH': ""}):
        assert_raises(pytest.skip.Exception, func, 2)
