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

from .session import POSIXSession


# For now just assuming that local shell is a POSIX shell
# Later we could specialize based on the OS, and that is why
# Resource/Shell is not subclassing Session but rather delegates to .session
class ShellSession(POSIXSession):
    """Local shell session"""

    def __init__(self):
        super(ShellSession, self).__init__()
        self._runner = None

    def start(self):
        self._runner = Runner()

    def stop(self):
        self._runner = None

    #
    # Commands fulfilling a "Session" interface to interact with the environment
    #
    def execute_command(self, command, env=None, cwd=None):
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
        out, err
        """
        # TODO: bring back updated_env?
        command_env = dict(self._env, **(env or {}))
        # XXX should it be a generic behavior to auto-start?
        if self._runner is None:
            self.start()
        run_kw = {}
        if command_env:
            # if anything custom, then we need to get original full environment
            # and update it with custom settings which we either "accumulated"
            # via set_envvar, or it was passed into this call.
            run_env = os.environ.copy()
            run_env.update(command_env)
            run_kw['env'] = run_env

        return self._runner.run(
            command,
            # For now we do not ERROR out whenever command fails or provides
            # stderr -- analysis will be done outside
            expect_fail=True,
            expect_stderr=True,
            **run_kw
        )  # , shell=True)


@attr.s
class Shell(Resource):

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

    def get_session(self, pty=False, shared=None):
        """
        Log into a container and get the command line
        """
        if pty:
            raise NotImplementedError
        if shared:
            raise NotImplementedError
        return ShellSession()