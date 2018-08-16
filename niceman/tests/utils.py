# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Miscellaneous utilities to assist with testing"""

import inspect
import os
import re
import tempfile
import platform
import multiprocessing
import logging
from six import PY2, text_type
from mock import patch
import pytest

from niceman.support.external_versions import external_versions
from six.moves.SimpleHTTPServer import SimpleHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer
from six import reraise

from functools import wraps
from os.path import exists, realpath, join as opj

from ..cmd import Runner
from ..utils import *
from ..dochelpers import borrowkwargs
from ..resource.docker_container import DockerContainer

# temp paths used by clones
_TEMP_PATHS_CLONES = set()


# pytest variants for nose.tools commands.  These exist to avoid unnecessary
# churn in tests that already use these names.  New code should use plain
# asserts to take advantage of pytest's assertion introspection.


def assert_equal(a, b, msg=None):
    assert a == b, msg or "{!r} != {!r}".format(a, b)


def assert_not_equal(a, b, msg=None):
    assert a != b, msg or "{!r} == {!r}".format(a, b)


def assert_greater(a, b, msg=None):
    assert a > b, msg or "{!r} > {!r}".format(a, b)


def assert_greater_equal(a, b, msg=None):
    assert a >= b, msg or "{!r} >= {!r}".format(a, b)


def assert_true(x, msg=None):
    assert x, msg or "{!r} is not true".format(x)


def assert_false(x, msg=None):
    assert not x, msg or "{!r} is not false".format(x)


def assert_in(x, collection, msg=None):
    assert x in collection, \
        msg or "{!r} not found in {!r}".format(x, collection)


def assert_not_in(x, collection, msg=None):
    assert x not in collection, \
        msg or "{!r} unexpectedly found in {!r}".format(x, collection)


def assert_is(a, b, msg=None):
    assert a is b, msg or "{!r} is not {!r}".format(a, b)


def assert_is_instance(a, b, msg=None):
    assert isinstance(a, b), \
        msg or "{!r} is not an instance of {!r}".format(a, b)


# additional shortcuts
assert_raises = pytest.raises
eq_ = assert_equal
neq_ = assert_not_equal
ok_ = assert_true
nok_ = assert_false
in_ = assert_in


# def create_tree_archive(path, name, load, overwrite=False, archives_leading_dir=True):
#     """Given an archive `name`, create under `path` with specified `load` tree
#     """
#     from ..support.archives import compress_files
#     dirname = file_basename(name)
#     full_dirname = opj(path, dirname)
#     os.makedirs(full_dirname)
#     create_tree(full_dirname, load, archives_leading_dir=archives_leading_dir)
#     # create archive
#     if archives_leading_dir:
#         compress_files([dirname], name, path=path, overwrite=overwrite)
#     else:
#         compress_files(list(map(basename, glob.glob(opj(full_dirname, '*')))),
#                        opj(pardir, name),
#                        path=opj(path, dirname),
#                        overwrite=overwrite)
#     # remove original tree
#     shutil.rmtree(full_dirname)


def create_tree(path, tree, archives_leading_dir=True):
    """Given a list of tuples (name, load) create such a tree

    if load is a tuple itself -- that would create either a subtree or an archive
    with that content and place it into the tree if name ends with .tar.gz
    """
    lgr.log(5, "Creating a tree under %s", path)
    if not exists(path):
        os.makedirs(path)

    if isinstance(tree, dict):
        tree = tree.items()

    for name, load in tree:
        full_name = opj(path, name)
        if isinstance(load, (tuple, list, dict)):
            # if name.endswith('.tar.gz') or name.endswith('.tar'):
            #     create_tree_archive(path, name, load, archives_leading_dir=archives_leading_dir)
            # else:
                create_tree(full_name, load, archives_leading_dir=archives_leading_dir)
        else:
            #encoding = sys.getfilesystemencoding()
            #if isinstance(full_name, text_type):
            #    import pydb; pydb.debugger()
            with open(full_name, 'w') as f:
                if PY2 and isinstance(load, text_type):
                    load = load.encode('utf-8')
                f.write(load)

#
# Addition "checkers"
#

#
# Helpers to test symlinks
#

def ok_symlink(path):
    """Checks whether path is either a working or broken symlink"""
    link_path = os.path.islink(path)
    if not link_path:
        raise AssertionError("Path {} seems not to be a symlink".format(path))


def ok_good_symlink(path):
    ok_symlink(path)
    rpath = realpath(path)
    ok_(exists(rpath),
        msg="Path {} seems to be missing.  Symlink {} is broken".format(
                rpath, path))


def ok_broken_symlink(path):
    ok_symlink(path)
    rpath = realpath(path)
    assert_false(exists(rpath),
            msg="Path {} seems to be present.  Symlink {} is not broken".format(
                    rpath, path))


def ok_startswith(s, prefix):
    ok_(s.startswith(prefix),
        msg="String %r doesn't start with %r" % (s, prefix))


def ok_endswith(s, suffix):
    ok_(s.endswith(suffix),
        msg="String %r doesn't end with %r" % (s, suffix))


def nok_startswith(s, prefix):
    assert_false(s.startswith(prefix),
        msg="String %r starts with %r" % (s, prefix))


def ok_generator(gen):
    assert_true(inspect.isgenerator(gen), msg="%s is not a generator" % gen)


def ok_file_has_content(path, content):
    """Verify that file exists and has expected content"""
    assert(exists(path))
    with open(path, 'r') as f:
        assert_equal(f.read(), content)


def assert_in_in(substr, lst):
    """Verify that a substring is in an element of a list"""
    for s in lst:
        if substr in s:
            return
    assert False, '"%s" is not in "%s"' % (substr, str(lst))

#
# Decorators
#

@optional_args
def with_tree(t, tree=None, archives_leading_dir=True, delete=True, **tkwargs):

    @wraps(t)
    def newfunc(*arg, **kw):
        tkwargs_ = get_tempfile_kwargs(tkwargs, prefix="tree", wrapped=t)
        d = tempfile.mkdtemp(**tkwargs_)
        create_tree(d, tree, archives_leading_dir=archives_leading_dir)
        try:
            return t(*(arg + (d,)), **kw)
        finally:
            if delete:
                rmtemp(d)
    return newfunc


lgr = logging.getLogger('niceman.tests')


class SilentHTTPHandler(SimpleHTTPRequestHandler):
    """A little adapter to silence the handler
    """
    def __init__(self, *args, **kwargs):
        self._silent = lgr.getEffectiveLevel() > logging.DEBUG
        SimpleHTTPRequestHandler.__init__(self, *args, **kwargs)

    def log_message(self, format, *args):
        if self._silent:
            return
        lgr.debug("HTTP: " + format % args)


def _multiproc_serve_path_via_http(hostname, path_to_serve_from, queue): # pragma: no cover
    chpwd(path_to_serve_from)
    httpd = HTTPServer((hostname, 0), SilentHTTPHandler)
    queue.put(httpd.server_port)
    httpd.serve_forever()


@optional_args
def serve_path_via_http(tfunc, *targs):
    """Decorator which serves content of a directory via http url
    """

    @wraps(tfunc)
    def newfunc(*args, **kwargs):

        if targs:
            # if a path is passed into serve_path_via_http, then it's in targs
            assert len(targs) == 1
            path = targs[0]

        elif len(args) > 1:
            args, path = args[:-1], args[-1]
        else:
            args, path = (), args[0]

        # There is a problem with Haskell on wheezy trying to
        # fetch via IPv6 whenever there is a ::1 localhost entry in
        # /etc/hosts.  Apparently fixing that docker image reliably
        # is not that straightforward, although see
        # http://jasonincode.com/customizing-hosts-file-in-docker/
        # so we just force to use 127.0.0.1 while on wheezy
        #hostname = '127.0.0.1' if on_debian_wheezy else 'localhost'
        hostname = '127.0.0.1'

        queue = multiprocessing.Queue()
        multi_proc = multiprocessing.Process(
            target=_multiproc_serve_path_via_http,
            args=(hostname, path, queue))
        multi_proc.start()
        port = queue.get(timeout=300)
        url = 'http://{}:{}/'.format(hostname, port)
        lgr.debug("HTTP: serving {} under {}".format(path, url))

        try:
            # Such tests don't require real network so if http_proxy settings were
            # provided, we remove them from the env for the duration of this run
            env = os.environ.copy()
            env.pop('http_proxy', None)
            with patch.dict('os.environ', env, clear=True):
                return tfunc(*(args + (path, url)), **kwargs)
        finally:
            lgr.debug("HTTP: stopping server under %s" % path)
            multi_proc.terminate()

    return newfunc


@optional_args
def without_http_proxy(tfunc):
    """Decorator to remove http*_proxy env variables for the duration of the test
    """

    @wraps(tfunc)
    def newfunc(*args, **kwargs):
        # Such tests don't require real network so if http_proxy settings were
        # provided, we remove them from the env for the duration of this run
        env = os.environ.copy()
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)
        with patch.dict('os.environ', env, clear=True):
            return tfunc(*args, **kwargs)

    return newfunc


@borrowkwargs(methodname=make_tempfile)
@optional_args
def with_tempfile(t, **tkwargs):
    """Decorator function to provide a temporary file name and remove it at the end

    Parameters
    ----------

    To change the used directory without providing keyword argument 'dir' set
    NICEMAN_TESTS_TEMPDIR.

    Examples
    --------

    ::

        @with_tempfile
        def test_write(tfile):
            open(tfile, 'w').write('silly test')
    """

    @wraps(t)
    def newfunc(*arg, **kw):
        with make_tempfile(wrapped=t, **tkwargs) as filename:
            return t(*(arg + (filename,)), **kw)

    return newfunc


def skip_if_no_network(func=None):
    """Skip test completely in NONETWORK settings

    If not used as a decorator, and just a function, could be used at the module level
    """

    def check_and_raise():
        if os.environ.get('NICEMAN_TESTS_NONETWORK'):
            pytest.skip("Skipping since no network settings",
                        allow_module_level=True)

    if func:
        @wraps(func)
        def newfunc(*args, **kwargs):
            check_and_raise()
            return func(*args, **kwargs)
        # right away tag the test as a networked test
        tags = getattr(newfunc, 'tags', [])
        newfunc.tags = tags + ['network']
        return newfunc
    else:
        check_and_raise()


def skip_if_on_windows(func):
    """Skip test completely under Windows
    """
    @wraps(func)
    def newfunc(*args, **kwargs):
        if on_windows:
            pytest.skip("Skipping on Windows", allow_module_level=True)
        return func(*args, **kwargs)
    return newfunc


def skip_if_no_apt_cache(func=None):
    """Skip test completely if apt is unavailable

    If not used as a decorator, and just a function, could be used at the module level
    """

    def check_and_raise():
        if not external_versions["cmd:apt-cache"]:
            pytest.skip("Skipping since apt-cache is not available",
                        allow_module_level=True)

    if func:
        @wraps(func)
        def newfunc(*args, **kwargs):
            check_and_raise()
            return func(*args, **kwargs)
        return newfunc
    else:
        check_and_raise()


def skip_if_no_svn():
    runner = Runner()
    try:
        # will raise OSError(errno=2) if the command is not found
        runner.run(['svnadmin', '--help'])
        runner.run(['svn', '--help'])
    except OSError as exc:
        if exc.errno == 2:
            pytest.skip('subversion is not installed',
                        allow_module_level=True)
    return


def skip_ssh(func=None):
    """Skips SSH tests if on windows or if environment variable
    NICEMAN_TESTS_SSH was not set
    """

    def check_and_raise():
        if not os.environ.get('NICEMAN_TESTS_SSH'):
            pytest.skip("Run this test by setting NICEMAN_TESTS_SSH",
                        allow_module_level=True)

    if func:
        @wraps(func)
        def newfunc(*args, **kwargs):
            if on_windows:
                pytest.skip("SSH currently not available on windows.",
                            allow_module_level=True)
            check_and_raise()
            return func(*args, **kwargs)
        return newfunc
    else:
        check_and_raise()


def skip_if_no_docker_container(container_name='testing-container'):
    """Test decorator that will skip a test if the Docker container the test is
    going to connect to is not running in the Docker engine.

    Parameters
    ----------
    container_name : str
        Name of the container that needs to be running for the test to work.

    Returns
    -------
    func
        Decorator function

    Raises
    ------
    SkipTest
    """
    def decorator(func):
        if not DockerContainer.is_container_running(container_name):
            pytest.skip("Docker container '{}' not running, "
                        "skipping test  {}".format(container_name, func.__name__),
                        allow_module_level=True)
        return func
    return decorator


def skip_if_no_docker_engine(func):
    """Test decorator that will skip a test if a Docker engine can't be found.

    Returns
    -------
    func
        Decorator function

    Raises
    ------
    SkipTest
    """
    if not DockerContainer.is_engine_running():
        pytest.skip("Docker not found, skipping test {}".format(func.__name__),
                    allow_module_level=True)
    return func


def skip_if_no_singularity(func):
    """Test decorator that will skip a test if the singularity executable is
    not found.
    
    Returns
    -------
    func
        Decorator function
    """
    # Make sure singularity is installed
    try:
        stdout, _ = Runner().run(['singularity', '--version'])
    except Exception:
        msg = "Singularity not installed, skipping test {}"
        pytest.skip(msg.format(func.__name__), allow_module_level=True)

    if stdout.startswith('2.2') or stdout.startswith('2.3'):
        # Running singularity instances and managing them didn't happen
        # until version 2.4. See: https://singularity.lbl.gov/archive/
        msg = "Singularity version >= 2.4 required, skipping test {}"
        pytest.skip(msg.format(func.__name__), allow_module_level=True)
    return func

@optional_args
def assert_cwd_unchanged(func, ok_to_chdir=False):
    """Decorator to test whether the current working directory remains unchanged

    Parameters
    ----------
    ok_to_chdir: bool, optional
      If True, allow to chdir, so this decorator would not then raise exception
      if chdir'ed but only return to original directory
    """

    @wraps(func)
    def newfunc(*args, **kwargs):
        cwd_before = os.getcwd()
        pwd_before = getpwd()
        exc_info = None
        try:
            func(*args, **kwargs)
        except:
            exc_info = sys.exc_info()
        finally:
            try:
                cwd_after = os.getcwd()
            except OSError as e:
                lgr.warning("Failed to getcwd: %s" % e)
                cwd_after = None

        if cwd_after != cwd_before:
            chpwd(pwd_before)
            if not ok_to_chdir:
                lgr.warning(
                    "%s changed cwd to %s. Mitigating and changing back to %s"
                    % (func, cwd_after, pwd_before))
                # If there was already exception raised, we better re-raise
                # that one since it must be more important, so not masking it
                # here with our assertion
                if exc_info is None:
                    assert_equal(cwd_before, cwd_after,
                                 "CWD changed from %s to %s" % (cwd_before, cwd_after))

        if exc_info is not None:
            reraise(*exc_info)

    return newfunc


@optional_args
def run_under_dir(func, newdir='.'):
    """Decorator to run tests under another directory

    It is somewhat ugly since we can't really chdir
    back to a directory which had a symlink in its path.
    So using this decorator has potential to move entire
    testing run under the dereferenced directory name -- sideeffect.

    The only way would be to instruct testing framework (i.e. nose
    in our case ATM) to run a test by creating a new process with
    a new cwd
    """

    @wraps(func)
    def newfunc(*args, **kwargs):
        pwd_before = getpwd()
        try:
            chpwd(newdir)
            func(*args, **kwargs)
        finally:
            chpwd(pwd_before)


    return newfunc


def assert_re_in(regex, c, flags=0):
    """Assert that container (list, str, etc) contains entry matching the regex
    """
    if not isinstance(c, (list, tuple)):
        c = [c]
    for e in c:
        if re.match(regex, e, flags=flags):
            return
    raise AssertionError("Not a single entry matched %r in %r" % (regex, c))


# List of most obscure filenames which might or not be supported by different
# filesystems across different OSs.  Start with the most obscure
OBSCURE_FILENAMES = (
    " \"';a&b/&cd `| ",  # shouldn't be supported anywhere I guess due to /
    " \"';a&b&cd `| ",
    " \"';abcd `| ",
    " \"';abcd | ",
    " \"';abcd ",
    " ;abcd ",
    " ;abcd",
    " ab cd ",
    " ab cd",
    "a",
    " abc d.dat ",  # they all should at least support spaces and dots
)

@with_tempfile(mkdir=True)
def get_most_obscure_supported_name(tdir):
    """Return the most obscure filename that the filesystem would support under TEMPDIR

    TODO: we might want to use it as a function where we would provide tdir
    """
    for filename in OBSCURE_FILENAMES:
        if on_windows and filename.rstrip() != filename:
            continue
        try:
            with open(opj(tdir, filename), 'w') as f:
                f.write("TEST LOAD")
            return filename  # it will get removed as a part of wiping up the directory
        except:
            lgr.debug("Filename %r is not supported on %s under %s",
                      filename, platform.system(), tdir)
            pass
    raise RuntimeError("Could not create any of the files under %s among %s"
                       % (tdir, OBSCURE_FILENAMES))


@optional_args
def with_testsui(t, responses=None):
    """Switch main UI to be 'tests' UI and possibly provide answers to be used"""

    @wraps(t)
    def newfunc(*args, **kwargs):
        from niceman.ui import ui
        old_backend = ui.backend
        try:
            ui.set_backend('tests')
            if responses:
                ui.add_responses(responses)
            ret = t(*args, **kwargs)
            if responses:
                responses_left = ui.get_responses()
                assert not len(responses_left), "Some responses were left not used: %s" % str(responses_left)
            return ret
        finally:
            ui.set_backend(old_backend)

    return newfunc
with_testsui.__test__ = False


def assert_is_subset_recur(a, b, subset_types=[]):
    """Asserts that 'a' is a subset of 'b' (recursive on dicts and lists)

    Parameters
    ----------
    a : dict or list
        The desired subset collection (items that must be in b)
    b : dict or list
        The superset collection
    subset_types : list
        List of classes (from list, dict) that allow subsets. Otherwise
        we use strict matching.
"""
    # Currently we only allow lists and dicts
    assert {list, dict}.issuperset(subset_types)
    # For dictionaries recursively check children that are in a
    if isinstance(a, dict) and isinstance(b, dict) and dict in subset_types:
        for key in a:
            if key not in b:
                raise AssertionError("Key %s is missing" % key)
            assert_is_subset_recur(a[key], b[key], subset_types)
    # For lists, recurse for every value a to make sure it is in b
    # (note: two items in a may match the same item in b)
    elif isinstance(a, list) and isinstance(b, list) and list in subset_types:
        for a_val in a:
            for b_val in b:
                try:
                    assert_is_subset_recur(a_val, b_val, subset_types)
                    break
                except AssertionError:
                    pass
            else:
                raise AssertionError("Array value %s is missing" % a_val)
    # For anything else check for straight equality
    else:
        if a != b:
            raise AssertionError("Value %s != %s" % (a, b))


def create_pymodule(directory):
    """Create a skeleton Python module in `directory`.

    Parameters
    ----------
    directory : str
        Path to a non-existing directory.
    """
    os.makedirs(directory)
    with open(os.path.join(directory, "setup.py"), "w") as ofh:
        ofh.write("""\
from setuptools import setup

setup(name='nmtest',
      version='0.1.0',
      py_modules=['nmtest'])""")

    with open(os.path.join(directory, "nmtest"), "w") as ofh:
        ofh.write("")


#
# Context Managers
#
