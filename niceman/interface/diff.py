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
from niceman.formats.niceman import NicemanProvenance
from ..distributions.debian import DebianDistribution

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
        prov1=Parameter(
            doc="NICEMAN provenance file", 
            metavar='prov1',
            constraints=EnsureStr()),
        prov2=Parameter(
            metavar="prov2",
            doc="NICEMAN provenance file", 
            constraints=EnsureStr())
    )

    @staticmethod
    def __call__(prov1, prov2):

        env_1 = NicemanProvenance(prov1).get_environment()
        env_2 = NicemanProvenance(prov2).get_environment()

        deb_pkgs_1 = get_debian_packages(env_1)
        deb_pkgs_2 = get_debian_packages(env_2)

        deb_pkgs_1_s = set(deb_pkgs_1)
        deb_pkgs_2_s = set(deb_pkgs_2)

        deb_pkgs_only_1 = deb_pkgs_1_s - deb_pkgs_2_s
        deb_pkgs_only_2 = deb_pkgs_2_s - deb_pkgs_1_s

        if deb_pkgs_only_1 or deb_pkgs_only_2:
            print('Debian packages:')
        if deb_pkgs_only_1:
            for (name, arch) in sorted(deb_pkgs_only_1):
                package = deb_pkgs_1[(name, arch)]
                print('< %s %s %s' % (name, arch, package.version))
        if deb_pkgs_only_2 and deb_pkgs_only_2:
            print('---')
        if deb_pkgs_only_2:
            for (name, arch) in sorted(deb_pkgs_only_2):
                package = deb_pkgs_2[(name, arch)]
                print('> %s %s %s' % (name, arch, package.version))

        for (name, arch) in deb_pkgs_1_s.intersection(deb_pkgs_2_s):
            package_1 = deb_pkgs_1[(name, arch)]
            package_2 = deb_pkgs_2[(name, arch)]
            if package_1.version != package_2.version:
                print('Debian package %s %s:' % (name, arch))
                print('< %s' % package_1.version)
                print('---')
                print('> %s' % package_2.version)

        files1 = set(env_1.files)
        files2 = set(env_2.files)

        files_1_only = files1 - files2
        files_2_only = files2 - files1

        if files_1_only or files_2_only:
            print('Files:')
            for fname in files_1_only:
                print('< %s' % fname)
            if files_1_only and files_2_only:
                print('---')
            for fname in files_2_only:
                print('> %s' % fname)

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

def get_debian_distribution(env):
    """get_debian_distribution(environment) -> distribution

    Returns the Debian distribution in the given envirionment.  Returns 
    None if there are no Debian distributions.  Raises ValueError if there 
    is more than one Debian distribution.
    """
    deb_dist = None
    for dist in env.distributions:
        if isinstance(dist, DebianDistribution):
            if deb_dist:
                raise ValueError('multiple Debian distributions found')
            deb_dist = dist
    return deb_dist

def get_debian_packages(env):
    """get_debian_packages(environment) -> dictionary

    Returns the Debian packages as a dictionary of (name, arch) -> package.  
    Returns an empty dictionary if there are no Debian distributions.  
    Propagates ValueError from get_debian_distribution() if there is more 
    than one Debian distribution.
    """
    deb_dist = get_debian_distribution(env)
    if not deb_dist:
        return {}
    return { (p.name, p.architecture): p for p in deb_dist.packages }
