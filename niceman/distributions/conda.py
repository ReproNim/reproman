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
import yaml

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
    files = attr.ib(default=attr.Factory(list))


# ~/anaconda
#
# ~/anaconda3
@attr.s
class CondaDistribution(Distribution):
    """
    Class to provide Conda package management.
    """

    path = attr.ib(default=None)
    packages = TypedList(CondaPackage)
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
        self._paths_cache = {}      # path -> False or CondaDistribution
        self._conda_info = {}       # path -> conda info
        self._env_export = {}       # path -> conda env export
        self._conda_packages = {}   # path -> conda package json details
        self._file_to_condapackage = {}  # file -> (path, package name)

    def _get_packagefields_for_files(self, files):
        raise NotImplementedError("TODO")

    def _create_package(self, *fields):
        raise NotImplementedError("TODO")

    def _get_conda_meta_files(self, conda_path):
        try:
            out, _ = self._session.run(
                'ls %s/conda-meta/*.json'
                % conda_path,
                expect_fail=True
            )
            return iter(out.splitlines())
        except Exception as exc:
            lgr.warning("Could not retrieve conda-meta files in path %s: %s",
                        conda_path, exc_str(exc))

    def _get_conda_package_details(self, conda_path):
        # TODO: Get details for pip installed packages
        packages = {}
        for meta_file in self._get_conda_meta_files(conda_path):
            try:
                out, err = self._session.run(
                    'cat %s' % meta_file,
                    expect_fail=True
                )
                details = json.loads(out)
#                print meta_file
#                print(json.dumps(details, indent=4))
                if "name" in details:
                    lgr.debug("Found conda package %s", details["name"])
                    # Packages are recorded in the conda environment as
                    # name=version=build
                    conda_package_name = \
                        ("%s=%s=%s" % (details["name"], details["version"],
                                       details["build"]))
                    packages[conda_package_name] = details
                    # Now map the package files to the package
                    for f in details["files"]:
                        full_path = os.path.normpath(os.path.join(conda_path,
                                                                  f))
                        self._file_to_condapackage[full_path] = \
                            (conda_path, conda_package_name)
            except Exception as exc:
                lgr.warning("Could not retrieve conda info in path %s: %s",
                            conda_path,
                            exc_str(exc))

        return packages

    def _get_conda_env_export(self, root_prefix, conda_path):
        export = {}
        try:
            # NOTE: We need to call conda-env directly.  Conda has problems
            # calling conda-env without a PATH being set...
            out, err = self._session.run(
                '%s/bin/conda-env export -p %s'
                % (root_prefix, conda_path),
                expect_fail=True
            )
            export = yaml.load(out)
        except Exception as exc:
            lgr.warning("Could not retrieve conda environment "
                        "export from path %s: %s", conda_path,
                        exc_str(exc))
        return export

    def _get_conda_info(self, conda_path):
        details = {}
        try:
            out, err = self._session.run(
                '%s/bin/conda info --json'
                % conda_path,
                expect_fail=True
            )
            details = json.loads(out)
        except Exception as exc:
            lgr.warning("Could not retrieve conda info in path %s: %s",
                        conda_path, exc_str(exc))
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

            # We found a new conda path, so retrieve and cache details
            self._conda_info[path] = self._get_conda_info(path)
            self._env_export[path] = self._get_conda_env_export(
                self._conda_info[path]["root_prefix"], path)
            self._conda_packages[path] = self._get_conda_package_details(path)
            # Create the distribution
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
        unknown_files = set()
        # First, loop through all the files and identify conda paths
        # This also pulls in conda environment information
        for path in paths:
            # Have we already found this path?
            if path in self._file_to_condapackage:
                lgr.debug("Already found %s " % path)
                continue
            # Path not found, so look for a new conda path
            dist = self._get_conda(path)
            if dist:
                if dist.path not in dists:
                    dists[dist.path] = dist
            else:
                unknown_files.add(path)

        # Now that we have the conda path info, identify the packages
        # TODO: associate packages to conda paths, and files to pachages
        # packages, remaining_files = self.identify_packages_from_files(files)

        # Assign names
        if len(dists) > 1:
            # needs indexes
            for idx, dist in enumerate(dists.values()):
                dist.name = 'conda-%d' % idx
        elif dists:
            list(dists.values())[0].name = 'conda'

        for dist in dists.values():
            yield dist, list(unknown_files)
