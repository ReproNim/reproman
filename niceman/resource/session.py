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


class Session(object):
    """Interface for Resources to provide interaction within that environment"""

    @abc.abstractmethod
    def execute_command(command, env=None):
        pass

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
    def read(self, path, mode='r'):
        """Return context manager to open files for reading or editing"""
        raise NotImplementedError()

    def mkdir(self, path, parents=False):
        """Create a directory (or with parent directories if `parents` 
        is True)
        """
        raise NotImplementedError
    # chmod?
    # chown?


class SessionRuntimeError(RuntimeError):
    pass


class POSIXSession(Session):
    """A Session which relies on commands present in any POSIX-compliant env"""

    def exists(self, path):
        """Return if file exists"""
        try:
            out, err = self.execute_command(["[", "-e", path, "]"])
        except Exception:  # TODO: More specific exception
            return False
        return True

    def lexists(self, path):
        """Return if file (or just a broken symlink) exists"""
        return os.path.lexists(path)

#    def get_mtime(self, path):
#

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