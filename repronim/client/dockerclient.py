# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Client sub-class to provide access to a Docker engine."""

from repronim.client.base import Client
import docker


class DockerClient(Client):

    def __init__(self, config):
        """
        Class constructor

        Parameters
        ----------
        config : dictionary
            Configuration parameters for the resource.
        """

        # Assign a default parameters if needed.
        if not 'engine_url' in config:
            config['engine_url'] = 'unix:///var/run/docker.sock'

        self._client = docker.DockerClient(config['engine_url'])

        super(DockerClient, self).__init__(config)