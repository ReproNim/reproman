# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Client sub-class to provide management of AWS subscription access."""

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

        # AWS client created for each individual environment. In this case,
        # the AWS client is needed to provide AWS subscription credentials.
        self._client = None

        super(AwsSubscription, self).__init__(resource_config)