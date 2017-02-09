# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to delete an environment
"""

__docformat__ = 'restructuredtext'

from .base import Interface
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..support.exceptions import InsufficientArgumentsError
from ..resource import ResourceConfig, Resource

from logging import getLogger
lgr = getLogger('niceman.api.delete')


class Delete(Interface):
    """Delete a computation environment

    Examples
    --------

      $ niceman delete --resource=my-resource --config=niceman.cfg

    """

    _params_ = dict(
        resource=Parameter(
            args=("-r", "--resource"),
            doc="""For which resource to create a new environment. To see
            available resource, run the command 'niceman ls'""",
            constraints=EnsureStr(),
        ),
        config = Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            constraints=EnsureStr(),
        ),
    )

    @staticmethod
    def __call__(resource, config):

        if not resource:
            raise InsufficientArgumentsError("Need a --resource")
        print("RESOURCE: {}".format(resource))

        resource_config = ResourceConfig(resource, config_path=config)
        env_resource = Resource.factory(resource_config)
        env_resource.delete()

        lgr.info("Deleted the environment %s", resource)