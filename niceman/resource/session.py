# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generic interface(s) for handling session interactions."""

import abc
import logging
lgr = logging.getLogger('niceman.resource.shell')

import os

from niceman.support.exceptions import SessionRuntimeError
from niceman.dochelpers import exc_str

import logging
lgr = logging.getLogger('niceman.session')


class Session(object):
    """Interface for Resources to provide interaction within that environment"""

    def __init__(self):
        # both will be maintained
        self._env = {}           # environment which would be in-effect only for this session
        self._env_permanent = {} # environment variables which would be in-effect in future sessions if resource is persisten

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    # By default don't do anything special
    def open(self):
        # XXX
        # we might right here already load possibly set permanent env variables
        # within that session?
        pass

    def close(self):
        # XXX may be here we should dump permanent env settings?
        pass

    def set_env(self, variable, value=None, permanent=False, format=False):
        """Set environment variable(s) to be used within the session
        
        All of them would be exported (TODO: should we allow for non-exported
        ones for some reason?  we aren't really scripting to care about non-exported)
        
        Parameters
        ----------
        variable: str or dict
          Variable name or entire dictionary of variable: value pairs (value
          must be undefined then).
        value: str or None
          If variable is not a dict, it would be the value for the variable
          to assign.  If value is None, removes that variable
        format: bool
          Use Python string `.format()` giving old value of the env dictionary
        """
        # XXX this is a generic handling but may be we should allow some
        # backends to handle it internally?  e.g. docker's ENV vs ARG
        for env in [self._env] + ([self._env_permanent] if permanent else []):
            if isinstance(variable, dict):
                assert value is None, "Must not provide new env as dict and a value"
                update_env = variable
            else:
                update_env = {variable: value}

            for newvar, newvalue in update_env.items():
                if newvalue is None and newvar in env:
                    del env[newvar]
                else:
                    if format:
                        newvalue = newvalue.format(env)
                    env[newvar] = newvalue
        if permanent:
            # We should store adjusted environment within the session for future
            # invocation
            raise NotImplementedError

    def get_env(self):
        """Query session environment settings"""
        # TODO: should we parametrize to be able to query for permanent ones
        # if were defined or those we store in our variables etc?
        raise NotImplementedError

    # TODO: move logic/handling of batched commands defined in
    # Resource  and probably env vars handling

    @abc.abstractmethod
    def execute_command(command, env=None):
        """Execute a command
        
        Parameters
        ----------
        env: dict, optional
          Additional settings for the environment.  If some variable needs
          to be un-defined, leave value to be None
        """
        raise NotImplementedError

    #
    # Files query and manipulation
    # TODO:  should be in subspace (.path) may be? This would allow for
    #        more flexible mixups
    @abc.abstractmethod
    def exists(self, path):
        """Return if file exists"""
        pass

    @abc.abstractmethod
    def copy_to(self, src_path, dest_path, preserve_perms=False,
                owner=None, group=None, recursive=False):
        """Take file on the local file system and copy over into the session
        """
        raise NotImplementedError

    @abc.abstractmethod
    def copy_from(self, src_path, dest_path, preserve_perms=False,
                  owner=None, group=None, recursive=False):
        raise NotImplementedError

    @abc.abstractmethod
    def get_mtime(self, path):
        raise NotImplementedError

    #
    # Somewhat optional since could be implemented with native "POSIX" commands
    #
    @abc.abstractmethod
    def read(self, path, mode='r'):
        """Return content of a file"""
        raise NotImplementedError

    @abc.abstractmethod
    def mkdir(self, path, parents=False):
        """Create a directory (or with parent directories if `parents` 
        is True)
        """
        raise NotImplementedError
    # chmod?
    # chown?


class POSIXSession(Session):
    """A Session which relies on commands present in any POSIX-compliant env"""


    def get_env(self):
        """Query session environment settings"""
        out, err = self.execute_command(
            ['python', '-c', 'import os; print(repr(os.environ).encode())']
        )
        env = eval(out.decode())
        return env

    def exists(self, path):
        """Return if file exists"""
        try:
            out, err = self.execute_command(["[", "-e", path, "]"])
        except Exception as exc:  # TODO: More specific exception?
            lgr.debug("Check for file presence failed: %s", exc_str(exc))
            return False
        if not err:
            return True
        else:
            lgr.debug("Standard error was not empty (%r), thus assuming that "
                      "test for file presence has failed", err)

    # def lexists(self, path):
    #     """Return if file (or just a broken symlink) exists"""
    #     return os.path.lexists(path)

# Seems to have no generic implementation in POSIX?  TODO: check
#  may be we could assume presence of e.g. python so we could use std library?
    def get_mtime(self, path):
        # TODO:  too common of a pattern -- we need a helper to wrap such calls
        out, err = self.execute_command(
            ['python', '-c', "import os, sys; print(os.path.getmtime(sys.argv[1]))", path]
        )
        return out.strip()

    #
    # Somewhat optional since could be implemented with native "POSIX" commands
    #
    def read(self, path):
        """Return context manager to open files for reading or editing"""
        out, err = self.execute_command(["cat", path])
        if err:
            raise SessionRuntimeError("Running had std error output: %s" % err)
        return out

    def mkdir(self, path, parents=False):
        """Create a directory
        """
        self.execute_command(["mkdir"] + ("-p" if parents else "") + [path])

    # chmod?
    # chown?