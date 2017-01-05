# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class to manage resources in which containers are created and run."""

import abc

from ..resource import Resource


class Client(Resource):
    """
    Base class for creating and managing compute resources.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        """
        Class constructor

        Parameters
        ----------
        config : dictionary
            Configuration parameters for the resource that will override
            the default settings from the repronim.cfg file
        """
        super(Client, self).__init__(config)

        self._connection = None
        self.connect()

    def get_connection(self):
        """
        Returns the connection object needed to communicate with the backend service.

        Returns
        -------
        Connection object specific to the backend API being implemented.
        """
        return self._connection

    @abc.abstractmethod
    def connect(self):
        """
        Connect to service and save client instance to _connection property.
        """
        return

    @abc.abstractmethod
    def list_environments(self):
        """
        Query the resource and return a list of container information.

        Returns
        -------
        Dictionary of containers located at the resource.
        """
        return {}

    @abc.abstractmethod
    def list_images(self):
        """
        Query the resource and return a list of image information.

        Returns
        -------
        Dictionary of images located at the resource.
        """
        return {}