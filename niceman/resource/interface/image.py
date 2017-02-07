# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Class interface definition for image resources."""

import abc


class Image(object):
    """
    Abstract class that defines the interface for an environment image.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def create(self, image_id, environment_resource):
        """
        Create an image from a running image.

        Parameters
        ----------
        image_id : string
            Identifier of the image to use when creating the image.
        envirnoment_resource : Resource instance ID
            An instance of a Resource/Environment class that is the base of
            the image to be created.
        """
        return

    @abc.abstractmethod
    def delete(self):
        """
        Remove an image from the backend.
        """
        return