# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Run internal NICEMAN (unit)tests to verify correct operation on the system"""


__docformat__ = 'restructuredtext'


import niceman
from .base import Interface


class Test(Interface):
    """Run internal NICEMAN (unit)tests.

    This can be used to verify correct operation on the system
    """
    @staticmethod
    def __call__():
        niceman.test()
