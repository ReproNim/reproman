# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""
import json
import os

import attr
from niceman.distributions import Distribution

from .base import SpecObject
from .base import DistributionTracer
from .base import Package
from .base import TypedList
from niceman.dochelpers import exc_str

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

    path = attr.ib(default=None)
    environments = TypedList(CondaEnvironment)
    channels = attr.ib(default=None)

    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        return

    def install_packages(self, session=None):
        """
        Install the packages associated to this distribution by the provenance
        into the environment environment.

        Parameters
        ----------
        session : object
            Environment sub-class instance.
        """

        # TODO: Need to figure out a graceful way to install conda before we can install packages here.
        # for package in self.provenance['packages']:
        #     session.add_command(['conda',
        #                            'install',
        #                            package['name']])
        return


class CondaTracer(DistributionTracer):
    """conda distributions tracer
    """

    def _init(self):
        self._paths_cache = {}  # path -> False or CondaDistribution

    def _get_packagefields_for_files(self, files):
        raise NotImplementedError("TODO")

    def _create_package(self, *fields):
        raise NotImplementedError("TODO")

    def _get_conda_details(self, path):
        details = {}
        try:
            out, err = self._session.run(
                '%s/bin/conda info --json'
                % path,
                expect_fail=True
            )
            details = json.loads(out)
            lgr.debug("Found conda details %s", json.dumps(details))
        except Exception as exc:
            lgr.warning("Could not retrieve conda info in path %s: %s", path,
                      exc_str(exc))
        return details

    def _get_conda(self, path):
        paths = []
        dist = None
        while path not in {None, os.path.pathsep, '', '/'}:
            if path in self._paths_cache:
                dist = self._paths_cache[path]
                break
            paths.append(path)
            try:
                _, _ = self._session.run(
                    'ls -ld %s/bin/conda %s/conda-meta'
                    % (path, path),
                    expect_fail=True
                )
            except Exception as exc:
                lgr.debug("Did not detect conda at the path %s: %s", path,
                          exc_str(exc))
                path = os.path.dirname(path)  # go to the parent
                continue

            details = self._get_conda_details(path)
            dist = CondaDistribution(
                name=None,  # to be assigned later
                path=path
                # TODO: all the packages and paths
            )
            lgr.info("Detected conda %s", dist)
            break

        for path in paths:
            self._paths_cache[path] = dist

        return dist

    def identify_distributions(self, paths):
        dists = {}  # conda_prefix -> CondaDistribution
        files_to_consider = paths[:]
        for path in paths:
            dist = self._get_conda(path)
            if dist and dist.path not in dists:
                dists[dist.path] = dist

            # TODO: check if path possibly within a conda distribution
            pass  # all the magic and slowly prune files_to_consider

        # Assign names
        if len(dists) > 1:
            # needs indexes
            for idx, dist in enumerate(dists.values()):
                dist.name = 'conda-%d' % idx
        elif dists:
            list(dists.values())[0].name = 'conda'

        for dist in dists.values():
            yield dist, files_to_consider
