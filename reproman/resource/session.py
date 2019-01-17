# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Generic interface(s) for handling session interactions."""

import logging

lgr = logging.getLogger('niceman.resource.session')

import attr
from functools import partial
import os
import os.path as op
import re
from six.moves import shlex_quote

from niceman.support.exceptions import SessionRuntimeError
from niceman.cmd import Runner
from niceman.dochelpers import exc_str, borrowdoc
from niceman.support.exceptions import CommandError
from niceman.utils import updated
from niceman.utils import to_unicode

import logging
lgr = logging.getLogger('niceman.session')


@attr.s
class Session(object):
    """Interface for Resources to provide interaction within that environment"""

    INTERNAL_COMMANDS = ['mkdir', 'isdir', 'put', 'get', 'chown', 'chmod']


    def __attrs_post_init__(self):
        """
        Maintain both current and future session environments.

        For persistent resources, we will save the environment information
        to make it available for sessions beyond the current one.
        """
        self._env = {}           # environment which would be in-effect only for this session
        self._env_permanent = {} # environment variables which would be in-effect in future sessions if resource is persistent

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __call__(self, *args, **kwargs):
        """Sugaring shortcut to `execute_command`"""
        return self.execute_command(*args, **kwargs)

    # By default don't do anything special
    def open(self):
        """
        Called when a session is started.
        """
        # XXX
        # we might right here already load possibly set permanent env variables
        # within that session?
        pass

    def close(self):
        """
        Called when a session ends.
        """
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
          to assign.  If value is None, removes that variable. Use empty string
          if you want it to be defined and empty
        permanent: bool, optional
          Store that variable for future session within this "container"
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
                        newvalue = newvalue.format(env[newvar])
                    env[newvar] = newvalue
        if permanent:
            # We should store adjusted environment within the session for future
            # invocation
            raise NotImplementedError

    def get_envvars(self, permanent=False):
        """Get stored session environment variables

        Parameters
        ----------
        permanent : {bool}, optional
            Indicate that the environment variables that persist across
            sessions should be returned (the default is False, which will
            return the environment variables specific to the current session.)

        Returns
        -------
        dict
            Key/value pairs of environment variables
        """
        # TODO: should we parametrize to be able to query for permanent ones
        # if were defined or those we store in our variables etc?
        return self._env_permanent if permanent else self._env

    def query_envvars(self):
        """Query full session environment settings within the session"""
        raise NotImplementedError

    def source_script(self, command, permanent=False, diff=True, shell=None):
        """Source a script which would modify the environment

        Note: if command is composite (e.g. "activate envname" for conda), it
        would work only in bash or zsh shell.

        Parameters
        ----------
        command : str or list
          Name of the script or composite command (if a list, such as
          ["activate", "envname"] in conda) to be "sourced"
        permanent : bool, optional
        diff : bool, optional
          Store only variables values of which were changed by sourcing the file
        shell : str, optional
          Which shell to use.  If none specified, the one specified by SHELL
          in the environment would be used. If that one is not specified -- /bin/sh
          will be used for simple command, or /bin/bash if composite

        Returns
        -------
        dict
            Key/value pairs of the new environment
        """
        raise NotImplementedError

    # TODO: move logic/handling of batched commands defined in
    # Resource  and probably env vars handling

    def execute_command(self, command, env=None, cwd=None):
        """
        Execute the given command in the environment.

        Parameters
        ----------
        command : list or str
            Shell command string or list of command tokens to send to the
            environment to execute.
        env : dict, optional
            Additional environment variables which are applied
            only to the current call.  If value is None -- variable will be
            removed
        cwd : string, optional
            Path of directory in which to run the command

        Returns
        -------
        (stdout, stderr)
        """
        # TODO: bring back updated_env?
        command_env = dict(self._env, **(env or {}))
        run_kw = {}
        if command_env:
            run_kw['env'] = command_env

        return self._execute_command(
            command,
            cwd=cwd,
            **run_kw
        )  # , shell=True)

    def _execute_command(self, command, env=None, cwd=None):
        """
        Execute the given command in the environment.

        Parameters
        ----------
        command : list or str
            Shell command string or list of command tokens to send to the
            environment to execute.
        env : dict, optional
            Additional environment variables which are applied
            only to the current call.  If value is None -- variable will be
            removed
        cwd : string, optional
            Path of directory in which to run the command

        Returns
        -------
        (stdout, stderr)

        Raises
        ------
        CommandError
           if command's exitcode wasn't 0 or None. exitcode is passed to
           CommandError's `code`-field. Command's stdout and stderr are stored
           in CommandError's `stdout` and `stderr` fields respectively.
        """
        raise NotImplementedError

    #
    # Files query and manipulation
    # TODO:  should be in subspace (.path) may be? This would allow for
    #        more flexible mixups

    def niceman_exec(self, command, args):
        """Run a niceman utility "exec" command in the environment

        Parameters
        ----------
        command : string
            The session method name to run. (e.g. mkdir, chown, etc.)
        args : list of strings
            Arguments passed in from the command line for the command

        Raises
        ------
        CommandError
            Exception if an invalid command argument is passed in.
        """

        if command not in self.INTERNAL_COMMANDS:
            raise CommandError(cmd=command, msg="Invalid command")

        pargs = [] # positional args to pass to session command
        kwargs = {} # key word args to pass to session command
        for arg in args:
            if '=' in arg:
                parts = arg.split('=')
                if len(parts) != 2:
                    raise CommandError(cmd=command,
                                       msg="Invalid command line parameter")
                kwargs[parts[0]] = parts[1]
            else:
                pargs.append(arg)

        getattr(self, command)(*pargs, **kwargs)

    def exists(self, path):
        """Determine if a path exists in the resource.

        Parameters
        ----------
        path : string
            Path to check for existence in the resource environment.

        Returns
        -------
        bool
            True if path exists
        """
        raise NotImplementedError

    def _prepare_dest_path(self, src_path, dest_path,
                           local=True, absolute_only=False):
        """Do common handling for the destination target of `get` and `put`.

        Parameters
        ----------
        src_path : str
            Path to source file.
        dest_path : str
            Path to target file.  If `dest_path` is None, the basename is taken
            from `src_path`.
        local : bool, optional
            Whether the destination is on the local machine.
        absolute_only : bool, optional
            Whether `dest_path` is required to be absolute.

        Returns
        -------
        The path to the destination, possibly adjusted to add the basename.
        """
        if local:
            exists = op.exists
            mkdir = os.makedirs
        else:
            exists = self.exists
            mkdir = partial(self.mkdir, parents=True)

        if absolute_only and not op.isabs(dest_path):
            raise ValueError(
                "Destination path must be absolute, got {}".format(dest_path))

        dest_dir = dest_base = None
        if dest_path:
            dest_dir, dest_base = op.split(dest_path)
            if dest_dir and not exists(dest_dir):
                mkdir(dest_dir)

        if not dest_base:
            dest_base = op.basename(src_path)
            dest_path = op.join(dest_dir, dest_base) if dest_dir else dest_base
        return dest_path

    def put(self, src_path, dest_path, uid=-1, gid=-1):
        """Take file on the local file system and copy over into the resource

        The src_path and dest_path must include the name of the file being
        transferred.

        Parameters
        ----------
        src_path : string
            Path to file to push to resource environment
        dest_path : string
            Path of resource directory to put local file in.  If this contains
            a trailing separator, it is considered directory and the base name
            is taken from `src_path`.
        uid : int, optional
            System user ID to assign ownership of file on resource  (the
            default is -1, which will preserve the user owner of the local file)
        gid : int, optional
            System group ID to assign group ownership of file on resource (the
            default is -1, which will preserve the group id of the local file)
        """
        raise NotImplementedError

    def get(self, src_path, dest_path=None, uid=-1, gid=-1):
        """Take file on the resource and copy over into the local system

        The src_path must include the name of the file being transferred.

        Parameters
        ----------
        src_path : string
            Path to file to pull from resource environment
        dest_path : string, optional
            Path in local file system to put local file in.  If unspecified,
            the destination path defaults the base name of `src_path` within
            the current directory.
        uid : int, optional
            System user ID to assign ownership of file on resource  (the
            default is -1, which will preserve the user owner of the local file)
        gid : int, optional
            System group ID to assign group ownership of file on resource (the
            default is -1, which will preserve the group id of the local file)
        """
        raise NotImplementedError

    def get_mtime(self, path):
        """Returns the modification time for a file in the resource

        Parameters
        ----------
        path : string
            Path to file on resource

        Returns
        -------
        string
            epoch timestamp

        """
        raise NotImplementedError

    #
    # Somewhat optional since could be implemented with native "POSIX" commands
    #
    def read(self, path, mode='r'):
        """Return content of a file

        Parameters
        ----------
        path : string
            Filesystem path to file to be read
        mode : string, optional
            Access mode when reading file (the default is 'r', which is read-only)

        Returns
        -------
        list of strings
            Contents of the file, one output line for each list item
        """
        raise NotImplementedError

    def mkdir(self, path, parents=False):
        """Create a directory

        Parameters
        ----------
        path : string
            Path to file in resource
        parents : bool, optional
            Include parent directories (the default is False)
        """
        raise NotImplementedError

    def mktmpdir(self):
        """Create a temporary directory and return the path

        Returns
        -------
        path : String
            Path to the created temporary directory
        """
        raise NotImplementedError

    def isdir(self, path):
        """Return True if path is pointing to a directory

        Parameters
        ----------
        path : string
            Path to test in the resource

        Returns
        -------
        bool
            True if path is a directory
        """
        raise NotImplementedError

    def chmod(self, path, mode, recursive=False):
        """Set the mode of the indicated path

        Parameters
        ----------
        path : string
            Path to file or directory whose permissions we want to update
        mode : string
            Octal number representing the permission bit pattern
        recursive : bool, optional
            Recurse the permission updates into the subdirectories (the default
            is False)
        """
        raise NotImplementedError

    def chown(self, path, uid=-1, gid=-1, recursive=False, remote=True):
        """Set the owner and group ownership of a file or directory.

        Parameters
        ----------
        path : string
            Path to file or directory whose ownship we want to update
        uid : number, optional
            System id of user (the default is -1, which leaves the existing
            user owner as is)
        gid : number, optional
            System id of group (the default is -1, which leaves the existing
            group owner as is)
        recursive : bool, optional
            Recurse into the path directory provided and update the ownership
            to all files and directories. (the default is False, which does
            not recurse)
        remote : bool, optional
            Runs the chown command to the path in the resource environment (the
            default is True, which runs in the resource environment, False
            runs the chown command in the local, host file system)
        """
        raise NotImplementedError


@attr.s
class POSIXSession(Session):
    """A Session which relies on commands present in any POSIX-compliant env

    """

    # -0 is not provided by busybox's env command.  So if we decide to make it
    # even more portable - something to be done
    _GET_ENVIRON_CMD = ['env', '-0']

    @borrowdoc(Session)
    def query_envvars(self):
        out, err = self.execute_command(self._GET_ENVIRON_CMD)
        env = self._parse_envvars_output(out)
        # TODO:  should we update with our .env or .env_permament????
        return env

    def _parse_envvars_output(self, out):
        """Decode a JSON string into an object

        Parameters
        ----------
        out : string
            JSON string to decode.

        Returns
        -------
        object
            Decoded representation of the JSON string
        """
        output = {}
        for line in to_unicode(out).split('\0'):
            if not line:
                continue
            split = line.split('=', 1)
            if len(split) != 2:
                lgr.warning(
                    "Failed to split envvar definition into key=value. Got %s", line)
                continue
            output[split[0]] = split[1]
        return output

    @borrowdoc(Session)
    def source_script(self, command, permanent=False, diff=True, shell=None):
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
            out, err = self.execute_command(self.exists_command(path))
        except Exception as exc:  # TODO: More specific exception?
            lgr.debug("Check for file presence failed: %s", exc_str(exc))
            return False
        if out == 'Found\n':
            return True
        else:
            lgr.debug("Standard error was not empty (%r), thus assuming that "
                      "test for file presence has failed", err)
            return False

    def exists_command(self, path):
        """Return the command to run for the exists method."""
        command = ['test', '-e', shlex_quote(path), '&&', 'echo', 'Found']
        return ['bash', '-c', ' '.join(command)]

    # def lexists(self, path):
    #     """Return if file (or just a broken symlink) exists"""
    #     return os.path.lexists(path)

    # Seems to have no generic implementation in POSIX?  TODO: check
    #  may be we could assume presence of e.g. python so we could use std library?
    def get_mtime(self, path):
        # TODO:  too common of a pattern -- we need a helper to wrap such calls
        out, err = self.execute_command(self.get_mtime_command(path))
        return out.strip()

    def get_mtime_command(self, path):
        """Return the command to run for the get_mtime method."""
        command = "import os, sys; print(os.path.getmtime(sys.argv[1]))"
        return ['python', '-c', command, path]

    #
    # Somewhat optional since could be implemented with native "POSIX" commands
    #
    def read(self, path, mode='r'):
        """Return context manager to open files for reading or editing"""
        out, err = self.execute_command(["cat", path])
        if err:
            raise SessionRuntimeError("Running had std error output: %s" % err)
        return out

    def mkdir(self, path, parents=False):
        """Create a directory
        """
        command = ["mkdir"]
        if parents: command.append("-p")
        command += [path]
        self.execute_command(command)

        if not self.isdir(path):
            raise CommandError(cmd='mkdir', msg="Failed to create directory")

    def mktmpdir(self):
        path, _ = self.execute_command(["mktemp", "-d"])
        return path.rstrip()  # Remove newline

    def isdir(self, path):
        try:
            out, err = self.execute_command(self.isdir_command(path))
        except Exception as exc:  # TODO: More specific exception?
            lgr.debug("Check for directory failed: %s", exc_str(exc))
            return False
        if out == 'Found\n':
            return True
        else:
            lgr.debug("Standard error was not empty (%r), thus assuming that "
                      "test for direcory has failed", err)
            return False

    def isdir_command(self, path):
        """Return the command to run for the isdir method."""
        command = ['test', '-d', shlex_quote(path), '&&', 'echo', 'Found']
        return ['bash', '-c', ' '.join(command)]

    def chmod(self, path, mode, recursive=False):
        """Set the mode of a remote path
        """
        command = ['chmod']
        if recursive: command += ["-R"]
        command += [mode] + [path]
        self.execute_command(command)

    def chown(self, path, uid=-1, gid=-1, recursive=False, remote=True):
        """Set the user and gid of a path
        """
        uid = int(uid) # Command line parameters getting passed as type str
        gid = int(gid)

        if uid == -1 and gid > -1:
            command = ['chgrp']
        else:
            command = ['chown']
        if recursive: command += ["-R"]
        if uid > -1 and gid > -1: command += ["{}.{}".format(uid, gid)]
        elif uid > -1: command += [uid]
        elif gid > -1: command += [gid]
        else: raise CommandError(cmd='chown', msg="Invalid command \
            parameters.")
        command += [path]
        if remote:
            self.execute_command(command)
        else:
            # Run on the local file system
            Runner().run(command)


def get_local_session(env={'LC_ALL': 'C'}, pty=False, shared=None):
    """A shortcut to get a local session"""
    # TODO: support arbitrary session as obtained from a resource
    # TODO:  Shell needs a name -- should we request from manager
    #        which would assume some magical name for reuse??
    from niceman.resource.shell import Shell
    session = Shell("localshell").get_session(pty=pty, shared=shared)
    # or we shouldn't set it ? XXXX
    if env:
        session.set_envvar(env)
    return session

def get_updated_env(env, update):
    """Given an environment and set of updates, return updated one

    Special handling -- keys with None for the value, will be removed
    """
    env_ = updated(env, update)
    # pop those explicitly set to None
    for e in list(env_):
        if env_[e] is None:
            del env_[e]
    return env_
