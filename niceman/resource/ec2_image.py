# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Resource sub-class to provide management of an AWS EC2 image."""

from .base import ResourceConfig, Resource
from .interface.image import Image

import logging
lgr = logging.getLogger('niceman.resource.ec2_image')

class Ec2Image(Resource, Image):

    def __init__(self, resource_config):
        """
        Class constructor

        Parameters
        ----------
        resource_config : ResourceConfig object
            Configuration parameters for the environment.
        """

        super(Ec2Image, self).__init__(resource_config)

        self._ec2_resource = None

        # Initialize the connection to the AWS resource.
        resource_config = ResourceConfig(resource_config['resource_backend'],
            config_path=resource_config['config_path'])
        aws_subscription = Resource.factory(resource_config)
        self._ec2_resource = aws_subscription()

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

    def delete(self):
        """
        Remove an image from the backend.
        """
        return
