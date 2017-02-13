# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Resource sub-class to provide management of a docker image."""

from .base import ResourceConfig, Resource
from .interface.image import Image

import logging
lgr = logging.getLogger('niceman.resource.docker_image')


class DockerImage(Resource, Image):

    def __init__(self, resource_config):
        """
        Class constructor

        Parameters
        ----------
        resource_config : ResourceConfig object
            Configuration parameters for the resource.
        """

        super(DockerImage, self).__init__(resource_config)

        self._client = None
        self._image = None

        # Open a client connection to the Docker engine.
        resource_config = ResourceConfig(resource_config['resource_backend'],
            config_path=resource_config['config_path'])
        docker_engine = Resource.factory(resource_config)
        self._client = docker_engine()

        # Search by image name.
        #         try:
        #             image = self._client.images.get(name_or_id)
        #         except docker.errors.ImageNotFound:
        #             lgr.error('No Docker resource found for {}'.format(name_or_id))
        #             return None

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
        Deletes an image from the Docker engine.
        """
        self._client.images.remove(self._image)