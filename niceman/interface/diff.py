# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Report if a specification satisfies the requirements in another specification
"""

import sys
import time

from .base import Interface
from ..support.constraints import EnsureStr
from ..support.exceptions import InsufficientArgumentsError
from ..support.param import Parameter

__docformat__ = 'restructuredtext'

from logging import getLogger
lgr = getLogger('niceman.api.retrace')

class MultipleDistributionsError(Exception):

    """multiple distributions of a given type found"""

    def __init__(self, cls):
        self.cls = cls

class Diff(Interface):
    """Report if a specification satisfies the requirements in another 
    specification

    Examples
    --------

      $ niceman diff --env environment.yml --req required_environment.yml

    """

    _params_ = dict(
        env=Parameter(
            args=("--env",),
            doc="NICEMAN environment specification", 
            metavar='env',
            constraints=EnsureStr()),
        req=Parameter(
            args=("--req",),
            metavar="req",
            doc="NICEMAN requirements", 
            constraints=EnsureStr())
    )

    @staticmethod
    def __call__(env, req):

        if not env:
            raise InsufficientArgumentsError("env undefined")

        if not req:
            raise InsufficientArgumentsError("req undefined")

        from niceman.formats.niceman import NicemanProvenance

        env_prov = NicemanProvenance(env)
        req_prov = NicemanProvenance(req)

#        print env_prov.get_environment()
        lgr.warning('diff: environment not checked')

        try:
            env_dists = dictify_distributions(env_prov.get_distributions())
        except MultipleDistributionsError as data:
            lgr.error('diff: panic!')
            fmt = 'multiple occurrences of %s in environment specification'
            raise ValueError(fmt % str(data.cls))

        try:
            req_dists = dictify_distributions(req_prov.get_distributions())
        except MultipleDistributionsError as data:
            lgr.error('diff: panic!')
            fmt = 'multiple occurrences of %s in requirements specification'
            raise ValueError(fmt % str(data.cls))

        needed_dists = []
        needed_packages = {}
        for dist_type in req_dists:
            if dist_type not in env_dists:
                needed_dists.append(dist_type)
                continue
            try:
                missing_packages = req_dists[dist_type] - env_dists[dist_type]
            except TypeError:
                fmt = '%s not checked (difference operator unsupported)'
                lgr.warning(fmt % dist_type)
                continue
            if missing_packages:
                needed_packages[dist_type] = missing_packages

        env_files = set(env_prov.get_files())
        req_files = set(req_prov.get_files())
        needed_files = req_files - env_files

        lgr.info('needed distributions: %d' % len(needed_dists))
        lgr.info('needed packages: %d' % len(needed_packages))
        lgr.info('needed files: %d' % len(needed_files))

        if not needed_dists and not needed_packages and not needed_files:
            # log line needed for test
            lgr.info('requirements satisfied')
            print 'requirements satisfied'

        if needed_dists:
            print 'needed distributions:'
            for dist in sorted(needed_dists):
                print '    %s' % dist

        if needed_packages:
            print 'needed packages:'
            for dist in sorted(needed_packages):
                print '    %s' % dist
                for package in sorted(needed_packages[dist], 
                                      key=lambda p: p.name.lower()):
                    if package.version:
                        print '        %s %s' % (package.name, package.version)
                    else:
                        print '        %s' % package.name

        if needed_files:
            print 'needed files:'
            for fname in sorted(needed_files):
                print '    %s' % fname

        return

def dictify_distributions(dist_list):
    """Make a dictionary of distributions from a list of distributions.

    Raises MultipleDistributionsError if more than one of a given type of 
    distribution is specified.
    """
    dist_dict = {}
    for dist in dist_list:
        dist_type = str(dist.__class__.__name__)
        if dist_type in dist_dict:
            raise MultipleDistributionsError(dist_type)
        dist_dict[dist_type] = dist
    return dist_dict
