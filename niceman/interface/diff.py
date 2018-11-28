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
from ..distributions.conda import CondaDistribution
from ..distributions.vcs import GitDistribution, SVNDistribution

__docformat__ = 'restructuredtext'

from logging import getLogger
lgr = getLogger('niceman.api.retrace')


class MultipleDistributionsError(Exception):
    """Multiple distributions of a given type found"""

    def __init__(self, cls):
        self.cls = cls


def _make_plural(s):
    """Poor man 'plural' version for now"""
    if s.endswith('repository'):
        return s.replace('repository', 'repositories')
    else:
        return s + 's'

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

        status = 0

        # distribution type -> package type string
        supported_distributions = {
            DebianDistribution: 'Debian package', 
            CondaDistribution: 'Conda package', 
            GitDistribution: 'Git repository',
            SVNDistribution: 'SVN repository'
        }

        env_1_dist_types = { d.__class__ for d in env_1.distributions }
        env_2_dist_types = { d.__class__ for d in env_2.distributions }
        all_dist_types = env_1_dist_types.union(env_2_dist_types)

        for dist_type in all_dist_types:

            if dist_type not in supported_distributions:

                pass

            else:

                pkg_type = supported_distributions[dist_type]

                dist_1 = env_1.get_distribution(dist_type)
                if dist_1:
                    pkgs_1 = {p._diff_cmp_id: p for p in dist_1.packages}
                else:
                    pkgs_1 = {}
                dist_2 = env_2.get_distribution(dist_type)
                if dist_2:
                    pkgs_2 = {p._diff_cmp_id: p for p in dist_2.packages}
                else:
                    pkgs_2 = {}

                pkgs_1_s = set(pkgs_1)
                pkgs_2_s = set(pkgs_2)

                pkgs_only_1 = pkgs_1_s - pkgs_2_s
                pkgs_only_2 = pkgs_2_s - pkgs_1_s

                if pkgs_only_1 or pkgs_only_2:
                    print(_make_plural(pkg_type) + ':')

                if pkgs_only_1:
                    for cmp_key in sorted(pkgs_only_1):
                        package = pkgs_1[cmp_key]
                        print('< %s' % package.diff_identity_string)
                        status = 3
                if pkgs_only_2 and pkgs_only_2:
                    print('---')
                if pkgs_only_2:
                    for cmp_key in sorted(pkgs_only_2):
                        package = pkgs_2[cmp_key]
                        print('> %s' % package.diff_identity_string)
                    status = 3

                for cmp_key in pkgs_1_s.intersection(pkgs_2_s):
                    package_1 = pkgs_1[cmp_key]
                    package_2 = pkgs_2[cmp_key]
                    if package_1._diff_vals != package_2._diff_vals:
                        print('%s %s:' % (pkg_type, " ".join(cmp_key)))
                        print('< %s' % package_1.diff_subidentity_string)
                        print('---')
                        print('> %s' % package_2.diff_subidentity_string)
                        status = 3

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
            status = 3

        return {'status': status}

    @staticmethod
    def result_renderer_cmdline(result):
        return result['status']
