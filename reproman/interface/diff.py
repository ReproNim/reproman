# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
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
from reproman.formats.reproman import RepromanProvenance
from ..distributions.debian import DebianDistribution
from ..distributions.conda import CondaDistribution
from ..distributions.vcs import GitDistribution, SVNDistribution
from ..distributions.venv import VenvDistribution, VenvEnvironment
from ..distributions.base import SpecDiff

__docformat__ = 'restructuredtext'

from logging import getLogger
lgr = getLogger('reproman.api.retrace')


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

      $ reproman diff environment1.yml environment2.yml

    """

    _params_ = dict(
        prov1=Parameter(
            doc="ReproMan provenance file", 
            metavar='prov1',
            constraints=EnsureStr()),
        prov2=Parameter(
            metavar="prov2",
            doc="ReproMan provenance file", 
            constraints=EnsureStr()), 
        satisfies=Parameter(
            args=("--satisfies", "-s"), 
            doc="Make sure the first environment satisfies the needs of the second environment", 
            action="store_true")
    )

    @staticmethod
    def __call__(prov1, prov2, satisfies):

        env_1 = RepromanProvenance(prov1).get_environment()
        env_2 = RepromanProvenance(prov2).get_environment()

        if satisfies:
            return Diff.satisfies(env_1, env_2)

        return Diff.diff(env_1, env_2)

    @staticmethod
    def diff(env_1, env_2):

        # distribution type -> package type string
        supported_distributions = {
            DebianDistribution: 'Debian package', 
            CondaDistribution: 'Conda package', 
            GitDistribution: 'Git repository',
            SVNDistribution: 'SVN repository', 
            VenvDistribution: 'Venv environment', 
        }

        env_1_dist_types = { d.__class__ for d in env_1.distributions }
        env_2_dist_types = { d.__class__ for d in env_2.distributions }
        all_dist_types = env_1_dist_types.union(env_2_dist_types)

        diffs = []

        for dist_type in all_dist_types:
            if dist_type not in supported_distributions:
                msg = 'diff doesn\'t know how to handle %s' % str(dist_type)
                raise ValueError(msg)
            dist_1 = env_1.get_distribution(dist_type)
            dist_2 = env_2.get_distribution(dist_type)
            diffs.append({'diff': SpecDiff(dist_1, dist_2), 
                          'pkg_type': supported_distributions[dist_type]})

        diffs.append({'diff': SpecDiff(env_1.files, env_2.files), 
                      'pkg_type': 'files'})

        files1 = set(env_1.files)
        files2 = set(env_2.files)

        return {'method': 'diff', 
                'diffs': diffs, 
                'files_1_only': files1 - files2, 
                'files_2_only': files2 - files1}

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

        for diff_d in result['diffs']:

            diff = diff_d['diff']
            pkg_type = diff_d['pkg_type']

            if pkg_type == 'files':
                files_diff = diff_d['diff']
                continue

            if diff.a_only or diff.b_only:
                print(_make_plural(pkg_type) + ':')
                status = 3
            for pkg_diff in diff.a_only:
                print('< %s' % pkg_diff.a.diff_identity_string)
            if diff.a_only and diff.b_only:
                print('---')
            for pkg_diff in diff.b_only:
                print('> %s' % pkg_diff.b.diff_identity_string)

            for pkg_diff in diff.a_and_b:
                if not hasattr(pkg_diff, 'collection'):
                    if pkg_diff.diff_vals_a != pkg_diff.diff_vals_b:
                        print('%s %s:' % (pkg_type, ' '.join(pkg_diff.diff_cmp_id)))
                        print('< %s' % pkg_diff.a.diff_subidentity_string)
                        print('---')
                        print('> %s' % pkg_diff.b.diff_subidentity_string)
                        status = 3
                else:
                    a_only = [ pd.a for pd in pkg_diff.a_only ]
                    b_only = [ pd.b for pd in pkg_diff.b_only ]
                    ab = [ pd for pd in pkg_diff.a_and_b 
                            if pd.diff_vals_a != pd.diff_vals_b ]
                    if a_only or b_only or ab:
                        print('%s %s:' % (pkg_type, ' '.join(pkg_diff.diff_cmp_id)))
                        for pkg in a_only:
                            print('< %s' % pkg.diff_identity_string)
                        for pd in ab:
                            print('< %s %s' % (pd.a.diff_identity_string, pd.a.diff_subidentity_string))
                        if (a_only and b_only) or ab:
                            print('---')
                        for pkg in b_only:
                            print('> %s' % pkg.diff_identity_string)
                        for pd in ab:
                            print('> %s %s' % (pd.b.diff_identity_string, pd.b.diff_subidentity_string))

        files_1_only = [ t[0] for t in files_diff.collection if t[1] is None ]
        files_2_only = [ t[1] for t in files_diff.collection if t[0] is None ]
        if files_1_only or files_2_only:
            print('Files:')
            for fname in files_1_only:
                print('< %s' % fname)
            if files_1_only and files_2_only:
                print('---')
            for fname in files_2_only:
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
