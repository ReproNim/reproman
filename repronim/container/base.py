# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class to manage container engines in which the environments are created."""

from importlib import import_module
import abc
from contextlib import contextmanager
import logging

class Container(object):
    """
    Base class for installing and managing container engines.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        """
        Class constructor

        Parameters
        ----------
        config : dictionary
            Configuration parameters for the container.
        """
        self.config = config
        self.command_buffer = []
        self.lgr = logging.getLogger('repronim.container')

    @staticmethod
    @contextmanager
    def factory(container_engine, config = {}):
        """
        Factory method for creating the appropriate Container sub-class.

        Parameters
        ----------
        container_engine : string
            Name of container engine. Current valid values are: 'dockerengine'
        config : dictionary
            Configuration parameters for the container.

        Returns
        -------
        Container sub-class instance.
        """
        class_name = container_engine.capitalize() + 'Container'
        module = import_module('repronim.container.' + container_engine)
        instance = getattr(module, class_name)(config)
        instance.create()
        yield instance
        instance.execute_command_buffer()

    @abc.abstractmethod
    def create(self, base_image_id=None):
        """
        Create a container instance.

        Parameters
        ----------
        base_image_id : string
            Identifier of the base image used to create the container.
        """
        return

    @abc.abstractmethod
    def execute_command(self, command):
        """
        Execute the given command in the container.

        Parameters
        ----------
        command : string or list
            Shell command string or list of command tokens to send to the
            container to execute.

        Returns
        -------
        list
            List of STDOUT lines from the container.
        """
        return

    def add_command(self, command):
        """
        Add a command to the command buffer so that all commands can be
        run at once in a batch submit to the container.

        Parameters
        ----------
        command : string or list
            Command string or list of command string tokens.
        """
        self.command_buffer.append(command)

    def execute_command_buffer(self):
        """
        Send all the commands in the command buffer to the container for
        execution.

        Returns
        -------
        list
            STDOUT lines from container
        """
        stdout = []
        for command in self.command_buffer:
            stdout + self.execute_command(command)

        return stdout