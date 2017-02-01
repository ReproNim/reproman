# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Backend resource class to provide access to a Docker engine."""

from .base import Resource
from .interface.backend import Backend
import docker


class DockerEngine(Resource, Backend):

    def __init__(self, resource_config):
        """
        Class constructor

        Parameters
        ----------
        resource_config : ResourceConfig object
            Configuration parameters for the resource.
        """

        # Assign a default parameters if needed.
        if not 'engine_url' in resource_config:
            resource_config['engine_url'] = 'unix:///var/run/docker.sock'

        self._client = docker.DockerClient(resource_config['engine_url'])

        super(DockerEngine, self).__init__(resource_config)