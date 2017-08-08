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
import re

from niceman.support.exceptions import SessionRuntimeError
from niceman.dochelpers import exc_str
from niceman.support.exceptions import CommandError

import logging
lgr = logging.getLogger('niceman.session')


class Session(object):
    """Interface for Resources to provide interaction within that environment"""

    def __init__(self):
        # both will be maintained
        self._env = {}           # environment which would be in-effect only for this session
        self._env_permanent = {} # environment variables which would be in-effect in future sessions if resource is persistent

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

    def set_envvar(self, variable, value=None, permanent=False, format=False):
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

    def get_envvars(self, permanent=False):
        """Get stored session environment variables"""
        # TODO: should we parametrize to be able to query for permanent ones
        # if were defined or those we store in our variables etc?
        return self._env_permanent if permanent else self._env

    def query_envvars(self):
        """Query full session environment settings within session"""
        raise NotImplementedError

    def source_script(self, script_or_cmd, permanent=False, diff=True):
        """Source a script which would modify the environment
        
        Parameters
        ----------
        permanent: bool, optional
        diff: bool, optional
          Store only variables values of which were changed by sourcing the file
        """
        raise NotImplementedError

    # TODO: move logic/handling of batched commands defined in
    # Resource  and probably env vars handling

    @abc.abstractmethod
    def execute_command(self, command, env=None, cwd=None):
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

    @abc.abstractmethod
    def isdir(self, path):
        """Return True if path is pointing to a directory
        """
        raise NotImplementedError


    # chmod?
    # chown?


class POSIXSession(Session):
    """A Session which relies on commands present in any POSIX-compliant env
    
    """

    _GET_ENVIRON_CMD = ['python', '-c', 'import os; print(repr(os.environ).encode())']

    def query_envvars(self):
        """Query session environment settings"""
        out, err = self.execute_command(self._GET_ENVIRON_CMD)
        env = self._parse_envvars_output(out)
        # TODO:  should we update with our .env or .env_permament????
        return env

    def _parse_envvars_output(self, out):
        return eval(out.decode())

    def source_script(self, command, permanent=False, diff=True, shell=None):
        """Source a script which would modify the environment

        Note: if command is composite (e.g. "activate envname" for conda), it
        would work only in bash or zsh shell.

        Parameters
        ----------
        command: str or list
          Name of the script or composite command (if a list, such as 
          ["activate", "envname"] in conda) to be "sourced"
        permanent: bool, optional
        diff: bool, optional
          Store only variables values of which were changed by sourcing the file
        shell: str, optional
          Which shell to use.  If none specified, the one specified by SHELL
          in the environment would be used. If that one is not specified -- /bin/sh
          will be used for simple command, or /bin/bash if composite
        """
        orig_env = self.query_envvars()
        # Might want to be reimplemented in derived classes?  e.g.
        # if session is persistent (i.e all commands run in persistent session)
        # and we don't need this source  to be permanent -- we could
        # just run it and be done
        marker = "== =NICEMAN == ="  # unique marker to be able to split away
        # possible output from the sourced script
        get_env_command = " ".join('"%s"' % s for s in self._GET_ENVIRON_CMD)
        shell = shell or self.query_envvars().get('SHELL', None)
        if not isinstance(command, list):
            command = [command]
            shell = shell or "/bin/sh"
        else:
            # apparently in purely POSIX shell (e.g. dash) you cannot do
            # parametric "source" calls, e.g. ". activate datalad".
            # Moreover e.g. conda supports only bash and zsh
            shell = shell or "/bin/bash"
        command = " ".join('"%s"' % c for c in command)
        out, err = self.execute_command(
            # is a composite command which would first source
            # and then run the same command we use in self.query_envvars
            # if it is all permanent
            [
                # Possibly use SHELL which was already set within the environment
                shell,
                '-c',
                '. {command}; echo "{marker}"; {get_env_command}'.format(**locals())
            ]
        )
        # stderr is ok -- above call might issue a warning
        # assert not err
        new_env = self._parse_envvars_output(
            re.sub('.*%s\n*' % marker, '', out, flags=re.DOTALL)
        )

        # TODO: deal with possible removals, so we should prune them from
        # local envs as well, warning if some variable wasn't even explicitly
        # listed locally

        # Apparently whenever it is a "parametric" command then shells insert
        # some "goodness" which I think we shouldn't care about
        if shell in ["zsh", "/bin/zsh"]:
            new_env.pop('_')
            new_env.pop('OLDPWD')
        elif shell in ["bash", "/bin/bash"]:
            new_env.pop('_')
            new_env.pop('SHLVL')

        if diff:
            # minimize by dropping the same as before
            for k in list(new_env.keys()):
                if k in orig_env and orig_env[k] == new_env[k]:
                    new_env.pop(k)

        env = self._env_permanent if permanent else self._env
        for k, v in new_env.items():
            env[k] = v

        return new_env

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

    def isdir(self, path):
        try:
            self.execute_command(['test', '-d', path])
            return True
        except CommandError:
            return False
    # chmod?
    # chown?