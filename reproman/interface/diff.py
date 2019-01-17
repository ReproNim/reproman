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

      $ niceman diff environment1.yml environment2.yml

    """

    _params_ = dict(
        prov1=Parameter(
            doc="NICEMAN provenance file", 
            metavar='prov1',
            constraints=EnsureStr()),
        prov2=Parameter(
            metavar="prov2",
            doc="NICEMAN provenance file", 
            constraints=EnsureStr()), 
        satisfies=Parameter(
            args=("--satisfies", "-s"), 
            doc="Make sure the first environment satisfies the needs of the second environment", 
            action="store_true")
    )

    @staticmethod
    def __call__(prov1, prov2, satisfies):

        env_1 = NicemanProvenance(prov1).get_environment()
        env_2 = NicemanProvenance(prov2).get_environment()

        if satisfies:
            return Diff.satisfies(env_1, env_2)

        return Diff.diff(env_1, env_2)

    @staticmethod
    def diff(env_1, env_2):

        result = {'method': 'diff', 'distributions': []}

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
                msg = 'diff doesn\'t know how to handle %s' % str(dist_type)
                raise ValueError(msg)
            dist_res = {'pkg_type': supported_distributions[dist_type], 
                        'pkg_diffs': []}
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
            dist_res['pkgs_1'] = pkgs_1
            dist_res['pkgs_2'] = pkgs_2
            pkgs_1_s = set(pkgs_1)
            pkgs_2_s = set(pkgs_2)
            dist_res['pkgs_only_1'] = pkgs_1_s - pkgs_2_s
            dist_res['pkgs_only_2'] = pkgs_2_s - pkgs_1_s
            for cmp_key in pkgs_1_s.intersection(pkgs_2_s):
                package_1 = pkgs_1[cmp_key]
                package_2 = pkgs_2[cmp_key]
                if package_1._diff_vals != package_2._diff_vals:
                    dist_res['pkg_diffs'].append((package_1, package_2))
            result['distributions'].append(dist_res)

        files1 = set(env_1.files)
        files2 = set(env_2.files)
        result['files_1_only'] = files1 - files2
        result['files_2_only'] = files2 - files1

        return result

    @staticmethod
    def satisfies(env_1, env_2):

        result = {'method': 'satisfies', 'distributions': []}

        # distribution type -> package type string
        supported_distributions = {
            DebianDistribution: 'Debian package'
        }

        env_1_dist_types = { d.__class__ for d in env_1.distributions }
        env_2_dist_types = { d.__class__ for d in env_2.distributions }
        all_dist_types = env_1_dist_types.union(env_2_dist_types)

        for dist_type in all_dist_types:
            if dist_type not in supported_distributions:
                msg = 'diff --satisfies doesn\'t know how to handle %s' % str(dist_type)
                raise ValueError(msg)
            unsatisfied_packages = []
            dist_1 = env_1.get_distribution(dist_type)
            dist_2 = env_2.get_distribution(dist_type)
            if not dist_2:
                continue
            for pkg in dist_2.packages:
                if not pkg.compare(dist_1, mode='satisfied_by'):
                    unsatisfied_packages.append(pkg)
            if unsatisfied_packages:
                dist_res = {'pkg_type': supported_distributions[dist_type], 
                            'packages': unsatisfied_packages}
                result['distributions'].append(dist_res)

        files1 = set(env_1.files)
        files2 = set(env_2.files)
        result['files'] = files2 - files1

        return result

    @staticmethod
    def result_renderer_cmdline(result):

        if result['method'] == 'diff':
            return Diff.render_cmdline_diff(result)
        return Diff.render_cmdline_satisfies(result)

    @staticmethod
    def render_cmdline_diff(result):

        status = 0

        for dist_res in result['distributions']:

            if dist_res['pkgs_only_1'] or dist_res['pkgs_only_2']:
                print(_make_plural(dist_res['pkg_type']) + ':')

            if dist_res['pkgs_only_1']:
                for cmp_key in sorted(dist_res['pkgs_only_1']):
                    package = dist_res['pkgs_1'][cmp_key]
                    print('< %s' % package.diff_identity_string)
                status = 3
            if dist_res['pkgs_only_1'] and dist_res['pkgs_only_2']:
                print('---')
            if dist_res['pkgs_only_2']:
                for cmp_key in sorted(dist_res['pkgs_only_2']):
                    package = dist_res['pkgs_2'][cmp_key]
                    print('> %s' % package.diff_identity_string)
                status = 3

            for (package_1, package_2) in dist_res['pkg_diffs']:
                print('%s %s:' % (dist_res['pkg_type'], 
                                  " ".join(package_1._diff_cmp_id)))
                print('< %s' % package_1.diff_subidentity_string)
                print('---')
                print('> %s' % package_2.diff_subidentity_string)
                status = 3

        if result['files_1_only'] or result['files_2_only']:
            print('Files:')
            for fname in result['files_1_only']:
                print('< %s' % fname)
            if result['files_1_only'] and result['files_2_only']:
                print('---')
            for fname in result['files_2_only']:
                print('> %s' % fname)
            status = 3

        return status


    @staticmethod
    def render_cmdline_satisfies(result):

        status = 0

        for dist_res in result['distributions']:
            print(_make_plural(dist_res['pkg_type']) + ':')
            for package in dist_res['packages']:
                print('> %s' % package.identity_string)
            status = 3

        if result['files']:
            print('Files:')
            for fname in result['files']:
                print('> %s' % fname)
            status = 3

        return status
