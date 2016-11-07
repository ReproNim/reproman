# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

import os
from repronim.container.base import Container
from repronim.cmd import Runner


class LocalhostContainer(Container):

    def __init__(self, config={}):
        super(LocalhostContainer, self).__init__(config)
        self._env = {}

    def create(self, base_image_id=None):
        """
        Create a container instance.

        Parameters
        ----------
        base_image_id : string
            Identifier of the base image used to create the container.
        """

        # Nothing to do to create the localhost "container".
        return


    def set_envvar(self, var, value):
        self._env[var] = value


    def execute_command(self, command, env=None):
        """
        Execute the given command in the container.

        Parameters
        ----------
        command : list
            Shell command string or list of command tokens to send to the
            container to execute.
        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call

        Returns
        -------
        list
            List of STDOUT lines from the container.
        """
        run = Runner()

        custom_env = self._env.copy()
        if env:
            custom_env.update(env)

        run_kw = {}
        if custom_env:
            # if anything custom, then we need to get original full environment
            # and update it with custom settings which we either "accumulated"
            # via set_envvar, or it was passed into this call.
            run_env = os.environ.copy()
            run_kw['env'] = run_env.update(custom_env)

        response = run(command, **run_kw)  # , shell=True)
        return [response]