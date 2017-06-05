# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

import attr
from niceman.distributions import Distribution

from .base import SpecObject
from .base import DistributionTracer
from .base import Package
from .base import TypedList
import logging
lgr = logging.getLogger('niceman.distributions.conda')


@attr.s
class CondaPackage(Package):
    name = attr.ib()


@attr.s
class CondaEnvironment(SpecObject):
    packages = TypedList(CondaPackage)

# ~/anaconda
#
# ~/anaconda3
@attr.s
class CondaDistribution(Distribution):
    """
    Class to provide Conda package management.
    """

    environments = TypedList(CondaEnvironment)
    channels = attr.s()

    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        return

    def install_packages(self, environment):
        """
        Install the packages associated to this distribution by the provenance
        into the environment environment.

        Parameters
        ----------
        environment : object
            Environment sub-class instance.
        """

        # TODO: Need to figure out a graceful way to install conda before we can install packages here.
        # for package in self.provenance['packages']:
        #     environment.add_command(['conda',
        #                            'install',
        #                            package['name']])
        return



class CondaTracer(DistributionTracer):
    """conda distributions tracer
    """

    def __init__(self, *args, **kwargs):
        super(CondaTracer, self).__init__(*args, **kwargs)
        self._paths_cache = {}  #  path -> False or CondaDistribution

    def _get_conda(self, path):
        import os
        paths = []
        dist = None
        while path not in {None, os.path.pathsep, ''}:
            if path in self._paths_cache:
                dist = self._paths_cache[path]
                break
            paths.append(path)
            try:
                out, err = self._session.run(
                    'ls -ld %s/bin/conda %s/conda-meta'
                    % (path, path)
                )
                # path is not a name
                dist = CondaDistribution(path)
                lgr.info("Detected conda %s", dist)
                break
            except Exception as exc:
                lgr.debug("Did not detect conda at the path %s", path)
            path = os.path.dirname(path)  # go to the parent
        for path in paths:
            self._paths_cache[path] = dist
        return dist


    def identify_distributions(self, paths):
        dists = {}  # conda_prefix -> CondaDistribution
        files_to_consider = paths[:]
        for path in paths:
            dist = self._get_conda(path)
            yield dist, files_to_consider

            # check if path possibly within a conda distribution
            pass  # all the magic and slowly prune files_to_consider

        for dist in dists.values():
            yield dist, files_to_consider
