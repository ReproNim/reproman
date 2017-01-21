# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Client sub-class to provide management of AWS subscription access."""

import boto3

from .base import Resource
from .interface.backend import Backend


class AwsSubscription(Resource, Backend):

    def __init__(self, resource_config):
        """
        Class constructor

        Parameters
        ----------
        config : ResourceConfig object
            Configuration parameters for the resource.
        """

        # Assign a default parameters if needed.
        if not 'region_name' in resource_config:
            resource_config['region_name'] = 'us-east-1'

        self._client = boto3.resource(
            'ec2',
            aws_access_key_id=resource_config['aws_access_key_id'],
            aws_secret_access_key=resource_config['aws_secret_access_key'],
            region_name=resource_config['region_name']
        )

        super(AwsSubscription, self).__init__(resource_config)