# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class interface definition for backend resources."""

import abc

import logging
lgr = logging.getLogger('niceman.resource.interface.backend')

class Backend(object):
    """
    Abstract class that defines the interface for a backend.
    """

    __metaclass__ = abc.ABCMeta

    def __call__(self, *args, **kwargs):
        """
        Returns the client object needed to communicate with the backend service.

        Returns
        -------
        Client object specific to the backend API being implemented.
        """
        lgr.debug("Retrieving resource client of type 'backend'.")
        return self._client