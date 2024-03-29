# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import collections
from collections.abc import Callable, Mapping
import re

import builtins
from shlex import quote as shlex_quote
import time

import os.path as op
from os.path import curdir, basename, exists, realpath, islink, join as opj, isabs, normpath, expandvars, expanduser, abspath
from urllib.parse import quote as urlquote, unquote as urlunquote, urlsplit

import logging
import shutil
import stat
import os
import os.path as op
import sys
import tempfile
import platform
import gc
import glob

import attr
from functools import wraps
from time import sleep
import inspect
from itertools import tee

from reproman.support.exceptions import CommandError

lgr = logging.getLogger("reproman.utils")

lgr.log(5, "Importing reproman.utils")
#
# Some useful variables
#
_platform_system = platform.system().lower()
on_windows = _platform_system == 'windows'
on_osx = _platform_system == 'darwin'
on_linux = _platform_system == 'linux'
try:
    linux_distribution = platform.linux_distribution()
    on_debian_wheezy = on_linux \
                       and linux_distribution[0] == 'debian' \
                       and linux_distribution[1].startswith('7.')
except:  # pragma: no cover
    on_debian_wheezy = False

#
# Little helpers
#

# `getargspec` has been deprecated in Python 3.
if hasattr(inspect, "getfullargspec"):
    def getargspec(func):
        """Backward-compatibility wrapper for inspect.getargspec.
        """
        # The first four elements in getfullargspec's return value match
        # getargspec's.
        return inspect.getfullargspec(func)[:4]
else:
    getargspec = inspect.getargspec


def get_func_kwargs_doc(func):
    """ Provides args for a function

    Parameters
    ----------
    func: str
      name of the function from which args are being requested

    Returns
    -------
    list
      of the args that a function takes in
    """
    return getargspec(func)[0]

    # TODO: format error message with descriptions of args
    # return [repr(dict(get_docstring_split(func)[1]).get(x)) for x in getargspec(func)[0]]


def assure_tuple_or_list(obj):
    """Given an object, wrap into a tuple if not list or tuple
    """
    if isinstance(obj, list) or isinstance(obj, tuple):
        return obj
    return (obj,)


def any_re_search(regexes, value):
    """Return if any of regexes (list or str) searches successfully for value"""
    for regex in assure_tuple_or_list(regexes):
        if re.search(regex, value):
            return True
    return False


def not_supported_on_windows(msg=None):
    """A little helper to be invoked to consistently fail whenever functionality is
    not supported (yet) on Windows
    """
    if on_windows:
        raise NotImplementedError("This functionality is not yet implemented for Windows OS"
                                  + (": %s" % msg if msg else ""))


def shortened_repr(value, l=30):
    try:
        if hasattr(value, '__repr__') and (value.__repr__ is not object.__repr__):
            value_repr = repr(value)
            if not value_repr.startswith('<') and len(value_repr) > l:
                value_repr = "<<%s...>>" % (value_repr[:l-8])
            elif value_repr.startswith('<') and value_repr.endswith('>') and ' object at 0x':
                raise ValueError("I hate those useless long reprs")
        else:
            raise ValueError("gimme class")
    except Exception as e:
        value_repr = "<%s>" % value.__class__.__name__.split('.')[-1]
    return value_repr


def __auto_repr__(obj):
    attr_names = tuple()
    if hasattr(obj, '__dict__'):
        attr_names += tuple(obj.__dict__.keys())
    if hasattr(obj, '__slots__'):
        attr_names += tuple(obj.__slots__)

    items = []
    for attr in sorted(set(attr_names)):
        if attr.startswith('_'):
            continue
        value = getattr(obj, attr)
        # TODO:  should we add this feature to minimize some talktative reprs
        # such as of URL?
        #if value is None:
        #    continue
        items.append("%s=%s" % (attr, shortened_repr(value)))

    return "%s(%s)" % (obj.__class__.__name__, ', '.join(items))

def auto_repr(cls):
    """Decorator for a class to assign it an automagic quick and dirty __repr__

    It uses public class attributes to prepare repr of a class

    Original idea: http://stackoverflow.com/a/27799004/1265472
    """

    cls.__repr__ = __auto_repr__
    return cls

def is_interactive():
    """Return True if all in/outs are tty"""
    # TODO: check on windows if hasattr check would work correctly and add value:
    #
    return sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()


import hashlib


def md5sum(filename):
    with open(filename, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def sorted_files(path):
    """Return a (sorted) list of files under path
    """
    return sorted(sum([[opj(r, f)[len(path)+1:] for f in files]
                       for r,d,files in os.walk(path)
                       if not '.git' in r], []))

from os.path import sep as dirsep
_VCS_REGEX = r'%s\.(?:git|gitattributes|svn|bzr|hg)(?:%s|$)' % (dirsep, dirsep)
_REPROMAN_REGEX = r'%s\.(?:reproman)(?:%s|$)' % (dirsep, dirsep)


def find_files(regex, topdir=curdir, exclude=None, exclude_vcs=True, exclude_reproman=False, dirs=False):
    """Generator to find files matching regex

    Parameters
    ----------
    regex: basestring
    exclude: basestring, optional
      Matches to exclude
    exclude_vcs:
      If True, excludes commonly known VCS subdirectories.  If string, used
      as regex to exclude those files (regex: `%r`)
    exclude_reproman:
      If True, excludes files known to be reproman meta-data files (e.g. under
      .reproman/ subdirectory) (regex: `%r`)
    topdir: basestring, optional
      Directory where to search
    dirs: bool, optional
      Either to match directories as well as files
    """

    for dirpath, dirnames, filenames in os.walk(topdir):
        names = (dirnames + filenames) if dirs else filenames
        # TODO: might want to uniformize on windows to use '/'
        paths = (opj(dirpath, name) for name in names)
        for path in filter(re.compile(regex).search, paths):
            path = path.rstrip(dirsep)
            if exclude and re.search(exclude, path):
                continue
            if exclude_vcs and re.search(_VCS_REGEX, path):
                continue
            if exclude_reproman and re.search(_REPROMAN_REGEX, path):
                continue
            yield path
find_files.__doc__ %= (_VCS_REGEX, _REPROMAN_REGEX)


def expandpath(path, force_absolute=True):
    """Expand all variables and user handles in a path.

    By default return an absolute path
    """
    path = expandvars(expanduser(path))
    if force_absolute:
        path = abspath(path)
    return path


def is_explicit_path(path):
    """Return whether a path explicitly points to a location

    Any absolute path, or relative path starting with either '../' or
    './' is assumed to indicate a location on the filesystem. Any other
    path format is not considered explicit."""
    path = expandpath(path, force_absolute=False)
    return isabs(path) \
        or path.startswith(os.curdir + os.sep) \
        or path.startswith(os.pardir + os.sep)

def rotree(path, ro=True, chmod_files=True):
    """To make tree read-only or writable

    Parameters
    ----------
    path : string
      Path to the tree/directory to chmod
    ro : bool, optional
      Either to make it R/O (default) or RW
    chmod_files : bool, optional
      Either to operate also on files (not just directories)
    """
    if ro:
        chmod = lambda f: os.chmod(f, os.stat(f).st_mode & ~stat.S_IWRITE)
    else:
        chmod = lambda f: os.chmod(f, os.stat(f).st_mode | stat.S_IWRITE | stat.S_IREAD)

    for root, dirs, files in os.walk(path, followlinks=False):
        if chmod_files:
            for f in files:
                fullf = opj(root, f)
                # might be the "broken" symlink which would fail to stat etc
                if exists(fullf):
                    chmod(fullf)
        chmod(root)


def rmtree(path, chmod_files='auto', *args, **kwargs):
    """To remove git-annex .git it is needed to make all files and directories writable again first

    Parameters
    ----------
    chmod_files : string or bool, optional
       Either to make files writable also before removal.  Usually it is just
       a matter of directories to have write permissions.
       If 'auto' it would chmod files on windows by default
    `*args` :
    `**kwargs` :
       Passed into shutil.rmtree call
    """
    # Give W permissions back only to directories, no need to bother with files
    if chmod_files == 'auto':
        chmod_files = on_windows

    if not os.path.islink(path):
        rotree(path, ro=False, chmod_files=chmod_files)
        shutil.rmtree(path, *args, **kwargs)
    else:
        # just remove the symlink
        os.unlink(path)


def rmtemp(f, *args, **kwargs):
    """Wrapper to centralize removing of temp files so we could keep them around

    It will not remove the temporary file/directory if REPROMAN_TESTS_KEEPTEMP
    environment variable is defined
    """
    if not os.environ.get('REPROMAN_TESTS_KEEPTEMP'):
        if not os.path.lexists(f):
            lgr.debug("Path %s does not exist, so can't be removed" % f)
            return
        lgr.log(5, "Removing temp file: %s" % f)
        # Can also be a directory
        if os.path.isdir(f):
            rmtree(f, *args, **kwargs)
        else:
            for i in range(10):
                try:
                    os.unlink(f)
                except OSError as e:
                    if i < 9:
                        sleep(0.1)
                        continue
                    else:
                        raise
                break
    else:
        lgr.info("Keeping temp file: %s" % f)


def file_basename(name, return_ext=False):
    """
    Strips up to 2 extensions of length up to 4 characters and starting with alpha
    not a digit, so we could get rid of .tar.gz etc
    """
    bname = basename(name)
    fbname = re.sub(r'(\.[a-zA-Z_]\S{1,4}){0,2}$', '', bname)
    if return_ext:
        return fbname, bname[len(fbname)+1:]
    else:
        return fbname


def escape_filename(filename):
    """Surround filename in "" and escape " in the filename
    """
    filename = filename.replace('"', r'\"').replace('`', r'\`')
    filename = '"%s"' % filename
    return filename


def encode_filename(filename):
    """Encode unicode filename
    """
    if isinstance(filename, str):
        return filename.encode(sys.getfilesystemencoding())
    else:
        return filename

if on_windows:
    def lmtime(filepath, mtime):
        """Set mtime for files.  On Windows a merely adapter to os.utime
        """
        os.utime(filepath, (time.time(), mtime))
else:
    def lmtime(filepath, mtime):
        """Set mtime for files, while not de-referencing symlinks.

        To overcome absence of os.lutime

        Works only on linux and OSX ATM
        """
        from .cmd import Runner
        # convert mtime to format touch understands [[CC]YY]MMDDhhmm[.SS]
        smtime = time.strftime("%Y%m%d%H%M.%S", time.localtime(mtime))
        lgr.log(3, "Setting mtime for %s to %s == %s", filepath, mtime, smtime)
        Runner().run(['touch', '-h', '-t', '%s' % smtime, filepath])
        rfilepath = realpath(filepath)
        if islink(filepath) and exists(rfilepath):
            # trust no one - adjust also of the target file
            # since it seemed like downloading under OSX (was it using curl?)
            # didn't bother with timestamps
            lgr.log(3, "File is a symlink to %s Setting mtime for it to %s",
                    rfilepath, mtime)
            os.utime(rfilepath, (time.time(), mtime))
        # doesn't work on OSX
        # Runner().run(['touch', '-h', '-d', '@%s' % mtime, filepath])


def assure_list(s):
    """Given not a list, would place it into a list. If None - empty list is returned

    Parameters
    ----------
    s: list or anything
    """

    if isinstance(s, list):
        return s
    elif s is None:
        return []
    else:
        return [s]


def assure_list_from_str(s, sep='\n'):
    """Given a multiline string convert it to a list of return None if empty

    Parameters
    ----------
    s: str or list
    """

    if not s:
        return None

    if isinstance(s, list):
        return s
    return s.split(sep)


def assure_dict_from_str(s, **kwargs):
    """Given a multiline string with key=value items convert it to a dictionary

    Parameters
    ----------
    s: str or dict

    Returns None if input s is empty
    """

    if not s:
        return None

    if isinstance(s, dict):
        return s

    out = {}
    for value_str in assure_list_from_str(s, **kwargs):
        if '=' not in value_str:
            raise ValueError("{} is not in key=value format".format(repr(value_str)))
        k, v = value_str.split('=', 1)
        if k in out:
            err  = "key {} was already defined in {}, but new value {} was provided".format(k, out, v)
            raise ValueError(err)
        out[k] = v
    return out

def only_with_values(d):
    """Given a dictionary, return the one only with entries which had non-null values"""
    # to maintain OrderedDict do explicit d.__class__
    return d.__class__((k, v) for k,v in d.items() if v)

def assure_bytes(s, encoding='utf-8'):
    """Convert/encode unicode to bytes if of 'str'

    Parameters
    ----------
    encoding: str, optional
      Encoding to use.  "utf-8" is the default
    """
    if not isinstance(s, str):
        return s
    return s.encode(encoding)


def assure_unicode(s, encoding=None, confidence=None):
    """Convert/decode to str if of 'bytes'

    Parameters
    ----------
    encoding: str, optional
      Encoding to use.  If None, "utf-8" is tried, and then if not a valid
      UTF-8, encoding will be guessed
    confidence: float, optional
      A value between 0 and 1, so if guessing of encoding is of lower than
      specified confidence, ValueError is raised
    """
    if not isinstance(s, bytes):
        return s
    if encoding is None:
        # Figure out encoding, defaulting to 'utf-8' which is our common
        # target in contemporary digital society
        try:
            return s.decode('utf-8')
        except UnicodeDecodeError as exc:
            from .dochelpers import exc_str
            lgr.debug("Failed to decode a string as utf-8: %s", exc_str(exc))
        # And now we could try to guess
        from chardet import detect
        enc = detect(s)
        denc = enc.get('encoding', None)
        if denc:
            denc_confidence = enc.get('confidence', 0)
            if confidence is not None and  denc_confidence < confidence:
                raise ValueError(
                    "Failed to auto-detect encoding with high enough "
                    "confidence. Highest confidence was %s for %s"
                    % (denc_confidence, denc)
                )
            return s.decode(denc)
        else:
            raise ValueError(
                "Could not decode value as utf-8, or to guess its encoding: %s"
                % repr(s)
            )
    else:
        return s.decode(encoding)


def unique(seq, key=None):
    """Given a sequence return a list only with unique elements while maintaining order

    This is the fastest solution.  See
    https://www.peterbe.com/plog/uniqifiers-benchmark
    and
    http://stackoverflow.com/a/480227/1265472
    for more information.
    Enhancement -- added ability to compare for uniqueness using a key function

    Parameters
    ----------
    seq:
      Sequence to analyze
    key: callable, optional
      Function to call on each element so we could decide not on a full
      element, but on its member etc
    """
    seen = set()
    seen_add = seen.add
    if not key:
        return [x for x in seq if not (x in seen or seen_add(x))]
    else:
        # OPT: could be optimized, since key is called twice, but for our cases
        # should be just as fine
        return [x for x in seq if not (key(x) in seen or seen_add(key(x)))]


def partition(items, predicate=bool):
    """Partition `items` by `predicate`.

    Parameters
    ----------
    items : iterable
    predicate : callable
        A function that will be mapped over each element in `items`. The
        elements will partitioned based on whether the return value is false or
        true.

    Returns
    -------
    A tuple with two generators, the first for 'false' items and the second for
    'true' ones.

    Notes
    -----
    Taken from Peter Otten's snippet posted at
    https://nedbatchelder.com/blog/201306/filter_a_list_into_two_parts.html
    """
    a, b = tee((predicate(item), item) for item in items)
    return ((item for pred, item in a if not pred),
            (item for pred, item in b if pred))


#
# Decorators
#

# Borrowed from pandas
# Copyright: 2011-2014, Lambda Foundry, Inc. and PyData Development Team
# License: BSD-3
def optional_args(decorator):
    """allows a decorator to take optional positional and keyword arguments.
        Assumes that taking a single, callable, positional argument means that
        it is decorating a function, i.e. something like this::

            @my_decorator
            def function(): pass

        Calls decorator with decorator(f, `*args`, `**kwargs`)"""

    @wraps(decorator)
    def wrapper(*args, **kwargs):
        def dec(f):
            return decorator(f, *args, **kwargs)

        is_decorating = not kwargs and len(args) == 1 and isinstance(args[0], Callable)
        if is_decorating:
            f = args[0]
            args = []
            return dec(f)
        else:
            return dec

    return wrapper


# TODO: just provide decorators for tempfile.mk* functions. This is ugly!
def get_tempfile_kwargs(tkwargs={}, prefix="", wrapped=None):
    """Updates kwargs to be passed to tempfile. calls depending on env vars
    """
    # operate on a copy of tkwargs to avoid any side-effects
    tkwargs_ = tkwargs.copy()

    # TODO: don't remember why I had this one originally
    # if len(targs)<2 and \
    if not 'prefix' in tkwargs_:
        tkwargs_['prefix'] = '_'.join(
            ['reproman_temp'] +
            ([prefix] if prefix else []) +
            ([''] if (on_windows or not wrapped)
                  else [wrapped.__name__]))

    directory = os.environ.get('REPROMAN_TESTS_TEMPDIR')
    if directory and 'dir' not in tkwargs_:
        tkwargs_['dir'] = directory

    return tkwargs_

@optional_args
def line_profile(func):
    """Q&D helper to line profile the function and spit out stats
    """
    import line_profiler
    prof = line_profiler.LineProfiler()

    @wraps(func)
    def newfunc(*args, **kwargs):
        try:
            pfunc = prof(func)
            return pfunc(*args, **kwargs)
        finally:
            prof.print_stats()
    return newfunc


def cached_property(prop):
    """Cache a property's return value.

    This avoids using `lru_cache`, which is more complicated than needed for
    simple properties and isn't available in Python 2's stdlib.

    Use this only if the property's return value is constant over the life of
    the object. This isn't appropriate for a property with a setter or a
    property whose getter value may change based some outside state.

    This should be positioned below the @property declaration.
    """
    # Modified from MIT-licensed
    # https://code.activestate.com/recipes/576563-cached-property/

    @wraps(prop)
    def wrapped(self):
        try:
            return self._property_cache[prop]
        except AttributeError:
            self._property_cache = {}
            x = self._property_cache[prop] = prop(self)
            return x
        except KeyError:
            x = self._property_cache[prop] = prop(self)
            return x
    return wrapped


#
# Context Managers
#

from contextlib import contextmanager

@contextmanager
def swallow_outputs():
    """Context manager to help consuming both stdout and stderr, and print()

    stdout is available as cm.out and stderr as cm.err whenever cm is the
    yielded context manager.
    Internally uses temporary files to guarantee absent side-effects of swallowing
    into StringIO which lacks .fileno.

    print mocking is necessary for some uses where sys.stdout was already bound
    to original sys.stdout, thus mocking it later had no effect. Overriding
    print function had desired effect
    """

    debugout = sys.stdout
    class StringIOAdapter(object):
        """Little adapter to help getting out/err values
        """
        def __init__(self):
            kw = get_tempfile_kwargs({}, prefix="outputs")

            self._out = open(tempfile.mktemp(**kw), 'w')
            self._err = open(tempfile.mktemp(**kw), 'w')

        def _read(self, h):
            with open(h.name) as f:
                return f.read()

        @property
        def out(self):
            self._out.flush()
            return self._read(self._out)

        @property
        def err(self):
            self._err.flush()
            return self._read(self._err)

        @property
        def handles(self):
            return self._out, self._err

        def cleanup(self):
            self._out.close()
            self._err.close()
            out_name = self._out.name
            err_name = self._err.name
            del self._out
            del self._err
            gc.collect()
            rmtemp(out_name)
            rmtemp(err_name)



    def fake_print(*args, **kwargs):
        sep = kwargs.pop('sep', ' ')
        end = kwargs.pop('end', '\n')
        file = kwargs.pop('file', sys.stdout)

        if file in (oldout, olderr, sys.stdout, sys.stderr):
            # we mock
            sys.stdout.write(sep.join(args) + end)
        else:
            # must be some other file one -- leave it alone
            oldprint(*args, sep=sep, end=end, file=file)

    from .ui import ui
    # preserve -- they could have been mocked already
    oldprint = getattr(builtins, 'print')
    oldout, olderr = sys.stdout, sys.stderr
    olduiout = ui.out
    adapter = StringIOAdapter()

    try:
        sys.stdout, sys.stderr = adapter.handles
        ui.out = adapter.handles[0]
        setattr(builtins, 'print', fake_print)

        yield adapter
    finally:
        sys.stdout, sys.stderr, ui.out = oldout, olderr, olduiout
        setattr(builtins, 'print',  oldprint)
        adapter.cleanup()


@contextmanager
def swallow_logs(new_level=None):
    """Context manager to consume all logs.

    """
    lgr = logging.getLogger("reproman")

    # Keep old settings
    old_level = lgr.level
    old_handlers = lgr.handlers

    # Let's log everything into a string
    # TODO: generalize with the one for swallow_outputs
    class StringIOAdapter(object):
        """Little adapter to help getting out values

        And to stay consistent with how swallow_outputs behaves
        """
        def __init__(self):
            kw = dict()
            get_tempfile_kwargs(kw, prefix="logs")

            self._out = open(tempfile.mktemp(**kw), 'w')

        def _read(self, h):
            with open(h.name) as f:
                return f.read()

        @property
        def out(self):
            self._out.flush()
            return self._read(self._out)

        @property
        def lines(self):
            return self.out.split('\n')

        @property
        def handle(self):
            return self._out

        def cleanup(self):
            self._out.close()
            out_name = self._out.name
            del self._out
            gc.collect()
            rmtemp(out_name)

    adapter = StringIOAdapter()
    lgr.handlers = [logging.StreamHandler(adapter.handle)]
    if old_level < logging.DEBUG:  # so if HEAVYDEBUG etc -- show them!
        lgr.handlers += old_handlers
    if isinstance(new_level, str):
        new_level = getattr(logging, new_level)

    if new_level is not None:
        lgr.setLevel(new_level)

    try:
        yield adapter
    finally:
        lgr.handlers = old_handlers
        lgr.setLevel(old_level)
        adapter.cleanup()


#
# Additional handlers
#
_sys_excepthook = sys.excepthook  # Just in case we ever need original one
def setup_exceptionhook(ipython=False):
    """Overloads default sys.excepthook with our exceptionhook handler.

       If interactive, our exceptionhook handler will invoke
       pdb.post_mortem; if not interactive, then invokes default handler.
    """

    def _reproman_pdb_excepthook(type, value, tb):
        import traceback
        traceback.print_exception(type, value, tb)
        print()
        if is_interactive():
            import pdb
            pdb.post_mortem(tb)

    if ipython:
        from IPython.core import ultratb
        sys.excepthook = ultratb.FormattedTB(mode='Verbose',
                                             # color_scheme='Linux',
                                             call_pdb=is_interactive())
    else:
        sys.excepthook = _reproman_pdb_excepthook


def assure_dir(*args):
    """Make sure directory exists.

    Joins the list of arguments to an os-specific path to the desired
    directory and creates it, if it not exists yet.
    """
    dirname = opj(*args)
    if not exists(dirname):
        os.makedirs(dirname)
    return dirname

def updated(d, update):
    """Return a copy of the input with the 'update'

    Primarily for updating dictionaries
    """
    d = d.copy()
    d.update(update)
    return d

def getpwd():
    """Try to return a CWD without dereferencing possible symlinks

    If no PWD found in the env, output of getcwd() is returned
    """
    try:
        return os.environ['PWD']
    except KeyError:
        return os.getcwd()

class chpwd(object):
    """Wrapper around os.chdir which also adjusts environ['PWD']

    The reason is that otherwise PWD is simply inherited from the shell
    and we have no ability to assess directory path without dereferencing
    symlinks.

    If used as a context manager it allows to temporarily change directory
    to the given path
    """
    def __init__(self, path, mkdir=False, logsuffix=''):

        if path:
            pwd = getpwd()
            self._prev_pwd = pwd
        else:
            self._prev_pwd = None
            return

        if not isabs(path):
            path = normpath(opj(pwd, path))
        if not os.path.exists(path) and mkdir:
            self._mkdir = True
            os.mkdir(path)
        else:
            self._mkdir = False
        lgr.debug("chdir %r -> %r %s", self._prev_pwd, path, logsuffix)
        os.chdir(path)  # for grep people -- ok, to chdir here!
        os.environ['PWD'] = path

    def __enter__(self):
        # nothing more to do really, chdir was in the constructor
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._prev_pwd:
            # Need to use self.__class__ so this instance, if the entire
            # thing mocked during the test, still would use correct chpwd
            self.__class__(self._prev_pwd, logsuffix="(coming back)")


def knows_annex(path):
    """Returns whether at a given path there is information about an annex

    It is just a thin wrapper around GitRepo.is_with_annex() classmethod
    which also checks for `path` to exist first.

    This includes actually present annexes, but also uninitialized ones, or
    even the presence of a remote annex branch.
    """
    from os.path import exists
    if not exists(path):
        lgr.debug("No annex: test path {0} doesn't exist".format(path))
        return False
    from reproman.support.gitrepo import GitRepo
    return GitRepo(path, init=False, create=False).is_with_annex()


@contextmanager
def make_tempfile(content=None, wrapped=None, **tkwargs):
    """Helper class to provide a temporary file name and remove it at the end (context manager)

    Parameters
    ----------
    mkdir : bool, optional (default: False)
        If True, temporary directory created using tempfile.mkdtemp()
    content : str or bytes, optional
        Content to be stored in the file created
    wrapped : function, optional
        If set, function name used to prefix temporary file name
    `**tkwargs`:
        All other arguments are passed into the call to tempfile.mk{,d}temp(),
        and resultant temporary filename is passed as the first argument into
        the function t.  If no 'prefix' argument is provided, it will be
        constructed using module and function names ('.' replaced with
        '_').

    To change the used directory without providing keyword argument 'dir' set
    REPROMAN_TESTS_TEMPDIR.

    Examples
    --------
        >>> from os.path import exists
        >>> from reproman.utils import make_tempfile
        >>> with make_tempfile() as fname:
        ...    k = open(fname, 'w').write('silly test')
        >>> assert not exists(fname)  # was removed

        >>> with make_tempfile(content="blah") as fname:
        ...    assert open(fname).read() == "blah"
    """

    if tkwargs.get('mkdir', None) and content is not None:
        raise ValueError("mkdir=True while providing content makes no sense")

    tkwargs_ = get_tempfile_kwargs(tkwargs, wrapped=wrapped)

    # if REPROMAN_TESTS_TEMPDIR is set, use that as directory,
    # let mktemp handle it otherwise. However, an explicitly provided
    # dir=... will override this.
    mkdir = tkwargs_.pop('mkdir', False)

    filename = {False: tempfile.mktemp,
                True: tempfile.mkdtemp}[mkdir](**tkwargs_)
    filename = realpath(filename)

    if content:
        with open(filename, 'w' + ('b' if isinstance(content, bytes) else '')) as f:
            f.write(content)

    if __debug__:
        # TODO mkdir
        lgr.debug('Created temporary thing named %s"' % filename)
    try:
        yield filename
    finally:
        # glob here for all files with the same name (-suffix)
        # would be useful whenever we requested .img filename,
        # and function creates .hdr as well
        lsuffix = len(tkwargs_.get('suffix', ''))
        filename_ = lsuffix and filename[:-lsuffix] or filename
        filenames = glob.glob(filename_ + '*')
        if len(filename_) < 3 or len(filenames) > 5:
            # For paranoid yoh who stepped into this already ones ;-)
            lgr.warning("It is unlikely that it was intended to remove all"
                        " files matching %r. Skipping" % filename_)
            return
        for f in filenames:
            try:
                rmtemp(f)
            except OSError:
                pass


def _path_(p):
    """Given a path in POSIX" notation, regenerate one in native to the env one"""
    if on_windows:
        return opj(p.split('/'))
    else:
        # Assume that all others as POSIX compliant so nothing to be done
        return p


def is_unicode(s):
    """Return true if an object is unicode"""
    return isinstance(s, str)


def is_binarystring(s):
    """Return true if an object is a binary string (not unicode)"""
    return isinstance(s, bytes)


def to_unicode(s, encoding="utf-8"):
    """Converts any type string to unicode"""
    if is_unicode(s):
        return s
    else:
        return s.decode(encoding=encoding)


def to_binarystring(s, encoding="utf-8"):
    """Converts any type string to binarystring"""
    if is_binarystring(s):
        return s
    else:
        return s.encode(encoding=encoding)


def safe_write(ostream, s, encoding="utf-8"):
    """Safely write different string types to an output stream"""
    try:  # Try unicode, and upon failure try binary_string
        ostream.write(to_unicode(s, encoding))
    except (TypeError, UnicodeEncodeError):
        ostream.write(to_binarystring(s, encoding))


def generate_unique_name(pattern, nameset):
    """Create a unique numbered name from a pattern and a set

    Parameters
    ----------
    pattern: basestring
      The pattern for the name (to be used with %) that includes one %d
      location
    nameset: collection
      Collection (set or list) of existing names. If the generated name is
      used, then add the name to the nameset.

    Returns
    -------
    str
      The generated unique name
    """
    i = 0
    while True:
        n = pattern % i
        i += 1
        if n not in nameset:
            return n


# http://stackoverflow.com/questions/1151658/python-hashable-dicts
class HashableDict(dict):
    """Dict that can be used as keys"""
    def __hash__(self):
        return hash(frozenset(self.values()))


def get_cmd_batch_len(arg_list, cmd_len):
    """Estimate the maximum batch length for a given argument list

    To make sure we don't call shell commands with too many arguments
    this function looks at an argument list and the command length without
    any arguments, and estimates the number of arguments we want to batch
    together at one time.

    Parameters
    ----------
    arg_list : list
      The list to process in the command
    cmd_len : number
      The length of the command without arguments

    Returns
    -------
    number
      The maximum number in a single batch
    """
    if not arg_list:
        raise ValueError("Cannot batch an empty argument list")
    # Pick a conservative max command-line length
    try:
        _MAX_LEN_CMDLINE = os.sysconf(str("SC_ARG_MAX")) // 2
    except (ValueError, AttributeError):
        _MAX_LEN_CMDLINE = 2048
    # Find out how many files we can query at once
    max_len = max(map(len, arg_list))
    return max((_MAX_LEN_CMDLINE - cmd_len) // (max_len + 1), 1)


def join_sequence_of_dicts(seq):
    """
    Joins a sequence of dicts into a single dict

    Parameters
    ----------
    seq: sequence
        Sequence of dicts to join

    Returns
    -------
    dict

    Raises
    ------
    RuntimeError if a duplicate key is encountered.
    """
    r = {}
    for d in seq:
        for k, v in d.items():
            if k in r:
                raise RuntimeError("Duplicate key %r (new value: %r, "
                                   "was: %r)" % (k, v, r[k]))
            r[k] = v
    return r


def cmd_err_filter(err_string):
    """
    Creates a filter for CommandErrors that match a specific error string

    Parameters
    ----------
    err_string: basestring
        The error string we want to match

    Returns
    -------
    func object -> boolean
    """
    return (lambda x: isinstance(x, CommandError) and
            err_string in to_unicode(x.stderr, "utf-8"))


def execute_command_batch(session, command, args, exception_filter=None):
    """
    Generator that executes session.execute_command, with batches of args

    We want to call commands like "apt-cache policy" on a large number of
    packages, but risk creating command-lines that are too long. This
    function is a generator that will call execute_command but with batches
    of arguments (to stay within the command-line length limit) and yield the
    results.

    Parameters
    ----------
    session
      Session object that implements the execute_command() member
    command : sequence
      The command that we wish to execute
    args : sequence
      The long list of additional arguments we wish to pass to the command
    exception_filter : func x -> bool
      A filter of exception types that the calling code will gracefully handle

    Returns
    -------
    (out, err, exception)
        stdout of the command, stderr of the command, and an exception
        that is in the list of expected exceptions

    """
    cmd_length = sum(map(len, command)) + len(command)
    num_args = get_cmd_batch_len(args, cmd_length)
    args = list(args)  # we might get in with a set
    while args:
        batch, args = args[:num_args], args[num_args:]
        try:
            out, err = session.execute_command(
                command + batch
            )
            out = to_unicode(out, "utf-8")
            yield (out, err, None)
        except Exception as e:
            if exception_filter and exception_filter(e):
                yield (None, None, e)
            else:
                raise


def items_to_dict(l, attrs='name', ordered=False):
    """Given a list of attr instances, return a dict using specified attrs as keys

    Parameters
    ----------
    attrs : str or list of str
      Which attributes of the items to use to group
    ordered : bool, optional
      Either to return an ordered dictionary following the original order of items in the list

    Raises
    ------
    ValueError
        If there is a conflict - multiple items with the same attrs used for key

    Returns
    -------
    dict or collections.OrderedDict
    """
    many = isinstance(attrs, (list, tuple))
    out = (collections.OrderedDict if ordered else dict)()
    for i in l:
        k = tuple(getattr(i, a) for a in attrs) if many else getattr(i, attrs)
        if k in out:
            raise ValueError(
                "We already saw entry for %s: %s.  Not adding %s",
                k, out[k], i
            )
        out[k] = i
    return out


# TODO: just absorb into SpecObject __init__ but would require more handling
# to allow *args as well

def instantiate_attr_object(item_type, items):
    """Instantiate item_type given items (for a list or dict)

    Provides a more informative exception message in case if some arguments
    are incorrect
    """
    try:
        if issubclass(item_type, list):
            return item_type(items)
        else:
            return item_type(**items)
    except TypeError as exc:
        if "unexpected keyword" in str(exc):
            known_kws = [i.name for i in item_type.__attrs_attrs__]
            incorrect_kws = set(items.keys()).difference(known_kws)
            if incorrect_kws:
                # Provide a more informative message
                raise TypeError(
                    "Following provided arguments are not known to %s: %s.  "
                    "Known but not yet provided are: %s"
                    % (item_type.__name__,
                       ', '.join(incorrect_kws),
                       ', '.join(sorted(set(known_kws).difference(items))))
                )
        # if couldn't figure it out -- just raise original
        raise


def attrib(*args, **kwargs):
    """Extend the attr.ib to include our metadata elements.

    ATM we support additional keyword args which are then stored within
    `metadata`:
    - `doc` for documentation to describe the attribute (e.g. in --help)

    Also, when the `default` argument of attr.ib is unspecified, set it to
    None.
    """
    doc = kwargs.pop('doc', None)
    metadata = kwargs.get('metadata', {})
    if doc:
        metadata['doc'] = doc
    if metadata:
        kwargs['metadata'] = metadata
    return attr.ib(*args, default=kwargs.pop('default', None), **kwargs)


class PathRoot(object):
    """Find the root of paths based on a predicate function.

    The path -> root mapping is cached across calls.

    Parameters
    ----------
    predicate : callable
        A callable that will be passed a path and should return true
        if that path should be considered a root.
    """
    def __init__(self, predicate):
        self._pred = predicate
        self._cache = {}  # path -> root

    def __call__(self, path):
        """Find root of `path` based on `predicate`.

        Parameters
        ----------
        path : str
            Find this path's root.

        Returns
        -------
        str or None
        """
        to_cache = []
        root = None
        for pth in self._walk_up(path):
            if pth in self._cache:
                root = self._cache[pth]
                break

            to_cache.append(pth)

            if self._pred(pth):
                root = pth
                break

        for pth in to_cache:
            self._cache[pth] = root
        return root

    @staticmethod
    def _walk_up(path):
        """Yield PATH, chopping off the right-most directory each iteration.

        Parameters
        ----------
        path : string
        """
        while path not in [os.path.pathsep, os.path.sep, ""]:
            yield path
            path = os.path.dirname(path)


def is_subpath(path, directory):
    """Test whether `path` is below (or is itself) `directory`.

    Symbolic links are not resolved before the check.
    """
    return not os.path.relpath(path, directory).startswith(os.path.pardir)


SemanticVersion = collections.namedtuple("SemanticVersion",
                                         ["major", "minor", "patch", "tag"])


def parse_semantic_version(version):
    """Split version into major, minor, patch, and tag components.

    Parameters
    ----------
    version : str
        A version string X.Y.Z.  X, Y, and Z must be digits.  Any remaining
        text is treated as a tag (e.g., "-rc1").

    Returns
    -------
    A namedtuple with the form (major, minor, patch, tag).
    """
    m = re.match(r"(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<patch>[0-9]+)"
                 r"(?P<tag>.*)",
                 version)
    if m:
        return SemanticVersion(*m.groups())
    else:
        raise ValueError(
            "{} does not appear to follow semantic versioning".format(version))


def command_as_string(command):
    """Convert `command` to the string representation.

    Parameters
    ----------
    command : list or str
        If it is a list, convert it to a string, quoting each element as
        needed.  If it is a string, it is returned as is.
    """
    if isinstance(command, list):
        command = " ".join(map(shlex_quote, command))
    return command


def merge_dicts(ds):
    """Convert an iterable of dictionaries.

    In the case of key collisions, the last value wins.

    Parameters
    ----------
    ds : iterable of dicts

    Returns
    -------
    dict
    """
    merged = {}
    for d in ds:
        merged.update(d)
    return merged


def parse_kv_list(params):
    """Create a dict from a "key=value" list.

    Parameters
    ----------
    params : sequence of str or mapping
        For a sequence, each item should have the form "<key>=<value".  If
        `params` is a mapping, it will be returned as is.

    Returns
    -------
    A mapping from backend key to value.

    Raises
    ------
    ValueError if item in `params` does not match expected "key=value" format.
    """
    if isinstance(params, Mapping):
        res = params
    elif params:
        def check_fmt(item):
            if "=" not in item:
                raise ValueError(
                    "Expected 'key=value' format but got '{}'"
                    .format(item))
            return item

        res = dict(p.split("=", 1) for p in map(check_fmt, params))
    else:
        res = {}
    return res


def write_update(fname, content, encoding=None):
    """Write `content` to `fname` unless it already has matching content.

    This is the same as simply writing the content, except no writing occurs if
    the content of the existing file matches, the write or update is logged,
    and the leading directories of `fname` are created if needed.

    Parameters
    ----------
    fname : str
        Path to update.
    content : str
        Content to dump to path.
    encoding : str or None, optional
        Passed to `open`.
    """
    existing_content = None
    if op.exists(fname):
        with open(fname, encoding=encoding) as fh:
            existing_content = fh.read()

    if content == existing_content:
        lgr.debug("File already has matching content: %s", fname)
    else:
        lgr.debug("%s content in %s",
                  "Updating" if existing_content else "Creating",
                  fname)
        os.makedirs(op.dirname(fname), exist_ok=True)
        with open(fname, "w", encoding=encoding) as fh:
            fh.write(content)


def pycache_source(path):
    """Map a pycache path to the original path.

    Parameters
    ----------
    path : str
        A Python cache file.

    Returns
    -------
    Path of cached Python file (str) or None if `path` doesn't look like a
    cache file.
    """
    if not (path.endswith(".pyc") or path.endswith(".pyo")):
        lgr.debug("Path does not look like a Python cache file: %s", path)
        return

    if "__pycache__" not in path:  # py2
        pyfile = path[:-1]
    else:
        # It should be a py3-style path, e.g., "__pycache__/f.cpython-35.pyc"
        # or "__pycache__/f.cpython-35.opt-2.pyc".
        leading, base = op.split(path)
        name = base.split(".", 1)[0]
        pyfile = op.join(leading[:-len("__pycache__")], name + ".py")
    lgr.debug("Converted pycache file %s to source file %s",
              path, pyfile)
    return pyfile


lgr.log(5, "Done importing reproman.utils")
