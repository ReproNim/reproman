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


    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    # By default don't do anything special
    def open(self):
        pass

    def close(self):
        pass

    @abc.abstractmethod
    def execute_command(command, env=None):
        pass

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