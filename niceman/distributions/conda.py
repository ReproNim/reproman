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
import re
from collections import defaultdict

import attr
import yaml

from niceman.distributions import Distribution

from .base import SpecObject
from .base import DistributionTracer
from .base import Package
from .base import TypedList
from .piputils import parse_pip_show
from niceman.dochelpers import exc_str
from niceman.utils import PathRoot

import logging
lgr = logging.getLogger('niceman.distributions.conda')


@attr.s
class CondaPackage(Package):
    name = attr.ib()
    installer = attr.ib()
    version = attr.ib()
    build = attr.ib()
    channel_name = attr.ib()
    size = attr.ib()
    md5 = attr.ib()
    url = attr.ib()
    origin_location = attr.ib(default=None)
    files = attr.ib(default=attr.Factory(list))


@attr.s
class CondaChannel(SpecObject):
    name = attr.ib()
    url = attr.ib(default=None)


@attr.s
class CondaEnvironment(SpecObject):
    name = attr.ib()
    path = attr.ib(default=None)
    packages = TypedList(CondaPackage)
    channels = TypedList(CondaChannel)


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
        self._env_path_root = PathRoot(self._is_conda_env_directory)
        self._root_path_root = PathRoot(self._is_conda_root_directory)

    def _get_packagefields_for_files(self, files):
        raise NotImplementedError("TODO")

    def _create_package(self, *fields):
        raise NotImplementedError("TODO")

    def _get_conda_meta_files(self, conda_path):
        try:
            out, _ = self._session.execute_command(
                'ls %s/conda-meta/*.json'
                % conda_path
            )
            return iter(out.splitlines())
        except Exception as exc:
            lgr.warning("Could not retrieve conda-meta files in path %s: %s",
                        conda_path, exc_str(exc))

    def _get_conda_package_details(self, conda_path):
        packages = {}
        file_to_package_map = {}
        for meta_file in self._get_conda_meta_files(conda_path):
            try:
                out, err = self._session.execute_command(
                    'cat %s' % meta_file
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
                        file_to_package_map[full_path] = conda_package_name
            except Exception as exc:
                lgr.warning("Could not retrieve conda info in path %s: %s",
                            conda_path,
                            exc_str(exc))

        return packages, file_to_package_map

    def _get_conda_pip_package_details(self, env_export, conda_path):
        packages = {}
        file_to_package_map = {}
        dependencies = env_export.get("dependencies", [])

        pip_deps = []
        for dep in dependencies:
            if isinstance(dep, dict) and "pip" in dep:
                pip_deps = dep.get("pip")

        for pip_dep in pip_deps:
            name, origin_location = self.parse_pip_package_entry(pip_dep)
            try:
                out, err = self._session.execute_command(
                    '%s/bin/pip show -f %s'
                    % (conda_path, name)
                )
                pip_info = parse_pip_show(out)
                # Record the details we care about
                details = {"name": pip_info.get("Name"),
                           "version": pip_info.get("Version"),
                           "installer": "pip",
                           "origin_location": origin_location}
                packages[pip_dep] = details
                # Map the package files to the package
                for f in pip_info.get("Files"):
                    full_path = os.path.normpath(
                        os.path.join(pip_info.get("Location"), f))
                    file_to_package_map[full_path] = pip_dep
            except Exception as exc:
                lgr.warning("Could not retrieve pip info "
                            "export from path %s: %s", conda_path,
                            exc_str(exc))
                continue

        return packages, file_to_package_map

    @staticmethod
    def parse_pip_package_entry(pip_dep):
        # Pip packages are recorded in conda exports as "name (loc)",
        # "name==version" or "name (loc)==version".  So split on "=", then
        # on " "
        name = pip_dep.split("=")[0]
        name = name.split(" ")[0]
        # Record the origin location (if installed from a local source)
        if "(" in pip_dep:  # We have an origin location
            origin_location = re.search('\(([^)]+)', pip_dep).group(1)
        else:
            origin_location = None
        return name, origin_location

    def _get_conda_env_export(self, root_prefix, conda_path):
        export = {}
        try:
            # NOTE: We need to call conda-env directly.  Conda has problems
            # calling conda-env without a PATH being set...
            out, err = self._session.execute_command(
                '%s/bin/conda-env export -p %s'
                % (root_prefix, conda_path)
            )
            export = yaml.load(out)
        except Exception as exc:
            if "unrecognized arguments: -p" in exc_str(exc):
                lgr.warning("Could not retrieve conda environment "
                            "export from path %s: "
                            "Please use Conda 4.3.19 or greater",
                            conda_path)
            else:
                lgr.warning("Could not retrieve conda environment "
                            "export from path %s: %s", conda_path,
                            exc_str(exc))
        return export

    def _get_conda_info(self, conda_path):
        details = {}
        try:
            out, err = self._session.execute_command(
                '%s/bin/conda info --json'
                % conda_path
            )
            details = json.loads(out)
        except Exception as exc:
            lgr.warning("Could not retrieve conda info in path %s: %s",
                        conda_path, exc_str(exc))
        return details

    def _get_conda_env_path(self, path):
        return self._env_path_root(path)

    def _is_conda_env_directory(self, path):
        return self._session.exists('%s/conda-meta' % path)

    def _get_conda_root_path(self, path):
        return self._root_path_root(path)

    def _is_conda_root_directory(self, path):
        return all(map(self._session.exists, ('%s/%s' % (path, d) for d in
                                              ('bin', 'envs', 'conda-meta'))))

    def identify_distributions(self, paths):
        conda_paths = set()
        root_to_envs = defaultdict(list)
        # Start with all paths being set as unknown
        unknown_files = set(paths)
        # Track count of found packages and files
        found_package_count = 0
        total_file_count = len(unknown_files)

        # First, loop through all the files and identify conda paths
        for path in paths:
            conda_path = self._get_conda_env_path(path)
            if conda_path:
                if conda_path not in conda_paths:
                    conda_paths.add(conda_path)

        # Loop through conda_paths, find packages and create the
        # environments
        for idx, conda_path in enumerate(conda_paths):
            # Start with an empty channels list
            channels = []
            found_channel_names = set()

            # Find the root path for the environment
            root_path = self._get_conda_root_path(conda_path)
            if not root_path:
                lgr.warning("Could not find root path for conda environment %s"
                            % conda_path)
                continue
            # Retrieve the environment details
            env_export = self._get_conda_env_export(
               root_path, conda_path)
            (conda_package_details, file_to_pkg) = \
                self._get_conda_package_details(conda_path)
            (conda_pip_package_details, file_to_pip_pkg) = \
                self._get_conda_pip_package_details(env_export, conda_path)
            # Join our conda and pip packages
            conda_package_details.update(conda_pip_package_details)
            file_to_pkg.update(file_to_pip_pkg)

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

                # Look up or create the conda channel for the environment list
                channel_name = details.get("schannel")
                if channel_name:
                    if channel_name not in found_channel_names:
                        # New channel for our environment, so add it
                        channel_url = details.get("channel")
                        found_channel_names.add(channel_name)
                        channels.append(CondaChannel(
                            name=channel_name,
                            url=channel_url))

                # Create the package
                package = CondaPackage(
                    name=details.get("name"),
                    installer=details.get("installer"),
                    version=details.get("version"),
                    build=details.get("build"),
                    channel_name=channel_name,
                    size=details.get("size"),
                    md5=details.get("md5"),
                    url=details.get("url"),
                    origin_location=details.get("origin_location"),
                    files=pkg_to_found_files[package_name]
                )
                packages.append(package)

            # Give the distribution a name
            # Determine name from path (Alt approach: use conda-env info)
            if os.path.normpath(conda_path) == os.path.normpath(root_path):
                env_name = "root"
            else:
                env_name = os.path.basename(os.path.normpath(conda_path))

            # Keep track of found package count
            found_package_count += len(packages)

            # Create the conda environment (works with root environments too)
            conda_env = CondaEnvironment(
                name=env_name,
                path=conda_path,
                packages=packages,
                channels=channels
            )
            root_to_envs[root_path].append(conda_env)

        lgr.info("%s: %d packages with %d files, and %d other files",
                 self.__class__.__name__,
                 found_package_count,
                 total_file_count - len(unknown_files),
                 len(unknown_files))

        # Find all the identified conda_roots
        conda_roots = root_to_envs.keys()
        # Loop through conda_roots and create the distributions
        for idx, root_path in enumerate(conda_roots):
            # Retrieve distribution details
            conda_info = self._get_conda_info(root_path)

            # Give the distribution a name
            if (len(conda_roots)) > 1:
                dist_name = 'conda-%d' % idx
            else:
                dist_name = 'conda'
            dist = CondaDistribution(
                name=dist_name,
                conda_version=conda_info.get("conda_version"),
                python_version=conda_info.get("python_version"),
                path=root_path,
                environments=root_to_envs[root_path]
            )
            yield dist, list(unknown_files)
