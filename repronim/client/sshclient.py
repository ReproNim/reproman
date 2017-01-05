# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Client sub-class to provide access via SSH to remote environments."""

from repronim.client.base import Client


class SshClient(Client):
    def __init__(self, config):
        """
        Class constructor

        Parameters
        ----------
        config : dictionary
            Configuration parameters for the resource.
        """

        super(SshClient, self).__init__(config)

    def connect(self):
        """
        Connect to service and save client instance to _client property.
        """
        return

    def list_environments(self):
        """
        Query the resource and return a list of container information.

        Returns
        -------
        Dictionary of containers located at the resource.
        """
        return {}

    def list_images(self):
        """
        Query the resource and return a list of image information.

        Returns
        -------
        Dictionary of images located at the resource.
        """
        return {}