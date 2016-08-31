# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to list available environments
"""

__docformat__ = 'restructuredtext'

from .base import Interface
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone, EnsureBool

from logging import getLogger
lgr = getLogger('repronim.api.ls')


class Ls(Interface):
    """List known computation environments

    Examples
    --------

      $ repronim ls
    """

    _params_ = dict(
        names=Parameter(
            doc="name of the specific environment(s) to be listed",
            metavar='NAME(s)',
            nargs="*",
            constraints=EnsureStr() | EnsureNone(),
        ),
        verbose=Parameter(
            args=("-v", "--verbose"),
            action="store_true",
            #constraints=EnsureBool() | EnsureNone(),
            doc="provide more verbose listing",
        ),
        # fast=Parameter(
        #     args=("-F", "--fast"),
        #     action="store_true",
        #     doc="only perform fast operations.  Would be overrident by --all",
        # ),
        # all=Parameter(
        #     args=("-a", "--all"),
        #     action="store_true",
        #     doc="list all entries, not e.g. only latest entries in case of S3",
        # ),
        # config_file=Parameter(
        #     doc="""path to config file which could help the 'ls'.  E.g. for s3://
        #     URLs could be some ~/.s3cfg file which would provide credentials""",
        #     constraints=EnsureStr() | EnsureNone()
        # ),
        # list_content=Parameter(
        #     choices=(None, 'first10', 'md5', 'full'),
        #     doc="""list also the content or only first 10 bytes (first10), or md5
        #     checksum of an entry.  Might require expensive transfer and dump
        #     binary output to your screen.  Do not enable unless you know what you
        #     are after""",
        #     default=None
        # ),
    )

    @staticmethod
    def __call__(names, verbose=False):
        raise NotImplementedError
