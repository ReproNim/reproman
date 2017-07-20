# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Resource sub-class to provide management of the localhost environment."""

import attr
from .base import Resource
from niceman.cmd import Runner

import logging
lgr = logging.getLogger('niceman.resource.shell')

import os

from .session import Session


@attr.s
class Shell(Resource, Session):

    # Container properties
    name = attr.ib()
    id = attr.ib(default=None)
    type = attr.ib(default='shell')

    status = attr.ib(default=None)

    def create(self):
        """
        Create a running environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to be created.
        """
        # Generic logic to reside in Resource???
        if self.id is None:
            self.id = Resource._generate_id()
        return {
            'id': self.id
        }

    def connect(self):
        """
        Connect to an existing environment.
        """
        return self

    def delete(self):
        """
        Remove this environment from the backend.
        """
        return

    def start(self):
        """
        Start this environment in the backend.
        """
        return self

    def stop(self):
        """
        Stop this environment in the backend.
        """
        return

    #
    # Commands fulfilling a "Session" interface to interact with the environment
    #
    def execute_command(self, command, env=None):
        """
        Execute the given command in the environment.

        Parameters
        ----------
        command : list
            Shell command string or list of command tokens to send to the
            environment to execute.
        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call

        Returns
        -------
        list
            List of STDOUT lines from the environment.
        """
        run = Runner()

        command_env = self.get_updated_env(env)

        run_kw = {}
        if command_env:
            # if anything custom, then we need to get original full environment
            # and update it with custom settings which we either "accumulated"
            # via set_envvar, or it was passed into this call.
            run_env = os.environ.copy()
            run_env.update(command_env)
            run_kw['env'] = run_env

        response = run(command, **run_kw)  # , shell=True)
        return [response]

    def exists(self, path):
        """Return if file exists"""
        return os.path.exists(path)

    def lexists(self, path):
        """Return if file (or just a broken symlink) exists"""
        return os.path.lexists(path)

    def copy_to(self, src_path, dest_path, preserve_perms=False,
                owner=None, group=None, recursive=False):
        """Take file on the local file system and copy over into the session
        """
        raise NotImplementedError

    def copy_from(self, src_path, dest_path, preserve_perms=False,
                  owner=None, group=None, recursive=False):
        raise NotImplementedError

    def get_mtime(self, path):
        return os.path.getmtime(path)

    #
    # Somewhat optional since could be implemented with native "POSIX" commands
    #
    def open(self, path, mode='r'):
        """Return context manager to open files for reading or editing"""
        raise NotImplementedError()

    def mkdir(self, path, leading=False):
        """Create a directory (or with leading directories if `leading` 
        is True)
        """
        raise NotImplementedError
    # chmod?
    # chown?