# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

from repronim.container.base import Container
from repronim.cmd import Runner


class LocalhostContainer(Container):

    def __init__(self, config = {}):
        super(LocalhostContainer, self).__init__(config)

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

    def execute_command(self, command):
        """
        Execute the given command in the container.

        Parameters
        ----------
        command : list
            Shell command string or list of command tokens to send to the
            container to execute.

        Returns
        -------
        list
            List of STDOUT lines from the container.
        """
        run = Runner()
        response = run(command, shell=True)
        return [response]