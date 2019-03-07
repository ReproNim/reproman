# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to delete an environment
"""

__docformat__ = 'restructuredtext'

from .base import Interface
import reproman.interface.base # Needed for test patching
from reproman.resource import get_manager
from .common_opts import resref_arg
from .common_opts import resref_type_opt

from logging import getLogger
lgr = getLogger('reproman.api.login')


class Login(Interface):
    """Log into a computation environment

    Examples
    --------

      $ reproman login my-resource

    """

    _params_ = dict(
        resref=resref_arg,
        resref_type=resref_type_opt,
    )

    @staticmethod
    def __call__(resref, resref_type="auto"):
        env_resource = get_manager().get_resource(resref, resref_type)

        # Connect to resource environment
        env_resource.connect()
        with env_resource.get_session(pty=True):
            pass
        # env_resource.login()
