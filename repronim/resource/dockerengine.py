# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Resource sub-class to provide access to a Docker engine."""

from repronim.resource.base import Resource


class DockerengineResource(Resource):

    def __init__(self, default_config={}, config={}):
        """
        Class constructor

        Parameters
        ----------
        default_config : dictionary
            Resource configuration settings from the repronim.cfg file.
        config : dictionary
            Configuration parameters for the resource that will override
            the default settings from the repronim.cfg file
        """

        # Assign a default parameters if needed.
        if not 'container' in default_config and not 'container' in config:
            default_config['container'] = 'dockercontainer'
        if not 'engine_url' in default_config and not 'engine_url' in config:
            default_config['engine_url'] = 'unix:///var/run/docker.sock'
        if not 'stdin_open' in default_config and not 'stdin_open' in config:
            default_config['stdin_open'] = True
        if not 'base_image_tag' in default_config and not 'base_image_tag' in config:
            default_config['base_image_tag'] = 'ubuntu:latest'

        super(DockerengineResource, self).__init__(default_config, config)

    def get_container_list(self):
        """
        Query the resource and return a list of container information.

        Returns
        -------
        List of containers located at the resource.
        """
        return

    def get_image_list(self):
        """
        Query the resource and return a list of image information.

        Returns
        -------
        List of images located at the resource.
        """
        return