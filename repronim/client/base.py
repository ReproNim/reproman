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

        # The _client attribute must be defined in the child class.
        if not hasattr(self, '_client'):
            raise RuntimeError("Unable to find the resource client for '{}'".format(config['resource_id']))

    def __call__(self, *args, **kwargs):
        """
        Returns the client object needed to communicate with the backend service.

        Returns
        -------
        Client object specific to the backend API being implemented.
        """
        self._lgr.debug("Retrieving client for resource {}".format(self['resource_id']))
        return self._client