# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of the localhost environment."""

import os
from niceman.environment.base import Environment
from niceman.cmd import Runner


class LocalshellEnvironment(Environment):

    def __init__(self, config={}):
        """
        Factory method for creating the appropriate Environment sub-class.

        Parameters
        ----------
        resource : object
            Resource sub-class instance
        config : dictionary
            Configuration parameters for the environment.

        Returns
        -------
        Environment sub-class instance.
        """
        super(LocalshellEnvironment, self).__init__(config)

    def create(self, name, image_id):
        """
        Create a running environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to be created.
        image_id : string
            Identifier of the image to use when creating the environment.
        """
        return

    def connect(self, name=None):
        """
        Connect to an existing environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to connect to.
        """
        return

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