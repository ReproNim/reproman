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
from collections import defaultdict

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
    version = attr.ib()
    build = attr.ib()
    channel = attr.ib()
    size = attr.ib()
    md5 = attr.ib()
    url = attr.ib()
    files = attr.ib(default=attr.Factory(list))

@attr.s
class CondaEnvironment(SpecObject):
    name = attr.ib()
    path = attr.ib(default=None)
    conda_version = attr.ib(default=None)
    python_version = attr.ib(default=None)
    packages = TypedList(CondaPackage)
    channels = attr.ib(default=None)

# ~/anaconda
#
# ~/anaconda3
@attr.s
class CondaDistribution(Distribution):
    """
    Class to provide Conda package management.
    """
    path = attr.ib(default=None)
    conda_version = attr.ib(default=None)
    python_version = attr.ib(default=None)
    packages = TypedList(CondaPackage)
    channels = attr.ib(default=None)
    environments = TypedList(CondaEnvironment)

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
        file_to_package_map = {}
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
                        full_path = os.path.normpath(
                            os.path.join(conda_path, f))
                        file_to_package_map[full_path] = conda_package_name;
            except Exception as exc:
                lgr.warning("Could not retrieve conda info in path %s: %s",
                            conda_path,
                            exc_str(exc))

        return packages, file_to_package_map

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

    def _get_conda_path(self, path):
        paths = []
        conda_path = None
        while path not in {None, os.path.pathsep, '', '/'}:
            if path in self._paths_cache:
                conda_path = self._paths_cache[path]
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

            conda_path = path
            lgr.info("Detected conda %s", conda_path)
            break

        for path in paths:
            self._paths_cache[path] = conda_path

        return conda_path

    def identify_distributions(self, paths):
        conda_paths = set()
        root_envs = []
        root_to_envs = defaultdict(list)
        # Start with all paths being set as unknown
        unknown_files = set(paths)

        # First, loop through all the files and identify conda paths
        for path in paths:
            conda_path = self._get_conda_path(path)
            if conda_path:
                if conda_path not in conda_paths:
                    conda_paths.add(conda_path)

        # Loop through conda_paths, find packages and create the
        # environments (note that conda_paths will grow)
        conda_env_idx = 0
        conda_root_idx = 0
        paths_to_process = set(conda_paths)
        while paths_to_process:
            conda_path = paths_to_process.pop()

            # Retrieve distribution details
            conda_info = self._get_conda_info(conda_path)
            # TODO: Use env_export to get pip packages
            root_path = conda_info["root_prefix"]
            env_export = self._get_conda_env_export(
               root_path, conda_path)
            (conda_package_details, file_to_pkg) = \
                self._get_conda_package_details(conda_path)

            # Add the root path to the list of conda_paths if not there
            if root_path not in conda_paths:
                conda_paths.add(root_path)
                paths_to_process.add(root_path)

            # Initialize a map from packages to files that defaults to []
            pkg_to_found_files = defaultdict(list)

            # Get the conda path prefix to calculate relative paths
            path_prefix = conda_path + os.path.sep
            # Loop through unknown files, assigning them to packages if found
            for path in set(unknown_files):  # Clone the set
                if path in file_to_pkg:
                    # The file was found so remove from unknown file set
                    unknown_files.remove(path)
                    # Make relative paths if it is begins with the conda path
                    if path.startswith(path_prefix):
                        rel_path = path[len(path_prefix):]
                    else:
                        rel_path = path
                    # And add to the package
                    pkg_to_found_files[file_to_pkg[path]].append(rel_path)

            packages = []
            # Create the packages in the environment
            for package_name in conda_package_details:
                details = conda_package_details[package_name]
#                print (json.dumps(details, indent=4))
                # Create the package
                package = CondaPackage(
                    name=details.get("name"),
                    version=details.get("version"),
                    build=details.get("build"),
                    channel=details.get("channel"),
                    size=details.get("size"),
                    md5=details.get("md5"),
                    url=details.get("url"),
                    files=pkg_to_found_files[package_name]
                )
                packages.append(package)

            # Create the Conda Environment or Distribution object
            if root_path == conda_path:
                # Name the root path
                name = 'conda_root-%d' % conda_root_idx
                conda_root_idx += 1
                # The conda path is a root path
                root_env = CondaDistribution(
                    name=name,
                    conda_version=conda_info.get("conda_version"),
                    python_version=conda_info.get("python_version"),
                    path=conda_path,
                    packages=packages,
                    channels=conda_info.get("channels"),
                    environments=[]
                )
                root_envs.append(root_env)
            else:
                # Name the conda path
                name = 'conda_env-%d' % conda_env_idx
                conda_env_idx += 1
                # The conda path is a non-root environment
                conda_env = CondaEnvironment(
                    name=name,
                    conda_version=conda_info.get("conda_version"),
                    python_version=conda_info.get("python_version"),
                    path=conda_path,
                    packages=packages,
                    channels=conda_info.get("channels")
                )
                root_to_envs[root_path].append(conda_env)

        # Loop through conda roots, update the environments and yield
        for root_env in root_envs:
            root_env.environments = root_to_envs[root_env.path]
            yield root_env, list(unknown_files)
