# emacs: -*- mode: python; py-indent-offset: 8; tab-width: 6; indent-tabs-mode: nil -*-
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
from niceman.resource.session import get_local_session

from niceman.distributions import Distribution, piputils
from niceman.dochelpers import exc_str
from niceman.support.exceptions import CommandError
from niceman.utils import attrib, PathRoot, is_subpath, make_tempfile

from .base import SpecObject
from .base import DistributionTracer
from .base import Package
from .base import TypedList


import logging
lgr = logging.getLogger('niceman.distributions.conda')


def get_conda_platform_from_python(py_platform):
    """
    Converts a python platform string to a corresponding conda platform

    Parameters
    ----------
    py_platform : str
        The python platform string

    Returns
    -------
    str
        The conda platform string

    """
    # Provides the conda platform mapping from conda/models/enum.py
    # Note that these are python prefixes (both 'linux2' and 'linux' from
    # python map to 'linux' in conda.)
    python_to_conda_platform_map = {
        'darwin': 'osx',
        'linux': 'linux',
        'openbsd': 'openbsd',
        'win': 'win',
        'zos': 'zos',
    }
    for k in python_to_conda_platform_map:
        if py_platform.startswith(k):
            return python_to_conda_platform_map[k]
    return None


def get_miniconda_url(conda_platform, python_version):
    """
    Gets the Miniconda install URL given the conda platform and python version

    Parameters
    ----------
    conda_platform : str
        The conda platform (e.g. "linux-64")

    python_version : str
        The python version (e.g. "2.7.1")

    Returns
    -------
    str
        The Miniconda insaller URL
    """
    if conda_platform.startswith("linux"):
        platform = "Linux"
    elif conda_platform.startswith("osx"):
        platform = "MacOSX"
    else:
        raise ValueError("Unsupported platform %s for conda installation" %
                         conda_platform)
    platform += "-x86_64" if ("64" in conda_platform) else "-x86"
    return "https://repo.continuum.io/miniconda/Miniconda%s-latest-%s.sh" \
                    % (python_version[0], platform)

@attr.s
class CondaPackage(Package):
    name = attrib(default=attr.NOTHING)
    installer = attrib()
    version = attrib()
    build = attrib()
    channel_name = attrib()
    size = attrib()
    md5 = attrib()
    url = attrib()
    location = attrib()
    editable = attrib(default=False)
    files = attrib(default=attr.Factory(list))

    _cmp_fields = ('name', 'build')

@attr.s
class CondaChannel(SpecObject):
    name = attrib(default=attr.NOTHING)
    url = attrib()


@attr.s
class CondaEnvironment(SpecObject):
    name = attrib(default=attr.NOTHING)
    path = attrib()
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
    path = attrib()
    conda_version = attrib()
    python_version = attrib()
    platform = attrib()
    environments = TypedList(CondaEnvironment)

    _cmp_field = ('path',)

    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        # TODO Move conda installation here (environment is actually session)
        return

    def install_packages(self, session=None):
        """
        Install the packages associated to this distribution by the provenance
        into the environment.

        Parameters
        ----------
        session : object
            Environment sub-class instance.

        Raises
        ------
        ValueError
            Unexpected conda platform or python version
        CommandError
            If unexpected error in install commands occurs
        """

        if not self.path:  # Permit empty conda config entry
            return

        if not session:
            session = get_local_session()

        # Use the session to make a temporary directory for our install files
        tmp_dir = session.mktmpdir()
        try:
            # Install Conda
            # See if Conda root path exists and if not, install Conda
            if not session.isdir(self.path):
                # TODO: Determine if we can detect miniconda vs anaconad
                miniconda_url = get_miniconda_url(self.platform,
                                                  self.python_version)
                session.execute_command("curl %s -o %s/miniconda.sh" %
                                        (miniconda_url, tmp_dir))
                # NOTE: miniconda.sh makes parent directories automatically
                session.execute_command("bash -b %s/miniconda.sh -b -p %s" %
                                        (tmp_dir, self.path))
            ## Update root version of conda
            session.execute_command(
               "%s/bin/conda install -y conda=%s python=%s" %
               (self.path, self.conda_version,
                self.get_simple_python_version(self.python_version)))

            # Loop through non-root packages, creating the conda-env config
            for env in self.environments:
                export_contents = self.create_conda_export(env)
                with make_tempfile(export_contents) as local_config:
                    remote_config = os.path.join(tmp_dir, env.name)
                    session.put(local_config, remote_config)
                    if not session.isdir(env.path):
                        try:
                            session.execute_command(
                                "%s/bin/conda-env create -p %s -f %s " %
                                (self.path, env.path, remote_config))
                        except CommandError:
                            # Some conda versions seg fault so try to update
                            session.execute_command(
                                "%s/bin/conda-env update -p %s -f %s " %
                                (self.path, env.path, remote_config))
                    else:
                        session.execute_command(
                            "%s/bin/conda-env update -p %s -f %s " %
                            (self.path, env.path, remote_config))

        finally:
            if tmp_dir:
                # Remove the tmp dir
                session.execute_command(["rm", "-R", tmp_dir])

        return

    @property
    def packages(self):
        return [ p for env in self.environments for p in env.packages ]

    @staticmethod
    def get_simple_python_version(python_version):
        # Get the simple python version from the conda info string
        # Specifically, pull "major.minor.micro" from the full string
        # "major.minor.micro.releaselevel.serial"
        return ".".join(python_version.split(".", 3)[:3])

    @staticmethod
    def format_conda_package(name, version=None, build=None, **_):
        # Note: Conda does not accept a build without a version
        return ("%s=%s=%s" % (name, version, build) if version and build
                 else ("%s=%s" % (name, version) if version
                       else "%s" % name))

    @staticmethod
    def format_pip_package(name, version=None, **_):
        return ("%s==%s" % (name, version) if version
                       else "%s" % name)

    @staticmethod
    def create_conda_export(env):
        # Collect the environment into a dictionary in the same manner as
        # https://github.com/conda/conda/blob/master/conda_env/env.py
        d = {}
        # TODO: The environment name should be discovered on retrace
        name = os.path.basename(os.path.normpath(env.path))
        d["name"] = name
        # Collect channels
        d["channels"] = [c.name for c in env.channels]
        # Collect packages (dependencies) with no installer
        d["dependencies"] = [
            CondaDistribution.format_conda_package(p.name, p.version, p.build)
            for p in env.packages
            if p.installer is None]
        #            p.get("name"), p.get("version"), p.get("build"))
        # Collect pip-installed dependencies
        pip_deps = [CondaDistribution.format_pip_package(p.name, p.version)
                    for p in env.packages
                    if p.installer is "pip"]
        if (pip_deps):
            d["dependencies"].append({"pip": pip_deps})
        # Add the prefix
        d["prefix"] = env.path
        # Now dump the export as a yaml file
        return yaml.safe_dump(d, default_flow_style=False)


class CondaTracer(DistributionTracer):
    """conda distributions tracer
    """

    def _init(self):
        self._get_conda_env_path = PathRoot(self._is_conda_env_path)

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
        except Exception as exc:  # Empty conda environment (unusual situation)
            lgr.warning("Could not retrieve conda-meta files in path %s: %s",
                        conda_path, exc_str(exc))
            return iter(())

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
        dependencies = env_export.get("dependencies", [])

        # If there are pip dependencies, they'll be listed under a
        # {"pip": [...]} entry.
        pip_pkgs = []
        for dep in dependencies:
            if isinstance(dep, dict) and "pip" in dep:
                # Pip packages are recorded in conda exports as "name (loc)",
                # "name==version" or "name (loc)==version".
                pip_pkgs = [p.split("=")[0].split(" ")[0] for p in dep["pip"]]
                break

        if not pip_pkgs:
            return {}, {}

        pip = conda_path + "/bin/pip"
        packages, file_to_package_map = piputils.get_package_details(
            self._session, pip, pip_pkgs)
        for entry in packages.values():
            entry["installer"] = "pip"
        return packages, file_to_package_map

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

    def _is_conda_env_path(self, path):
        return self._session.exists('%s/conda-meta' % path)

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
            # TODO: cache/memoize for those paths which have been considered
            # since will be asked again below
            conda_info = self._get_conda_info(conda_path)
            root_path = conda_info.get('root_prefix')
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

                location = details.get("location")
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
                    location=location,
                    editable=details.get("editable"),
                    files=pkg_to_found_files[package_name]
                )
                packages.append(package)

                # Make editable pip packages available to other tracers.
                if location and not is_subpath(location, conda_path):
                    unknown_files.add(location)

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

        lgr.debug(
            "%s: %d packages with %d files, and %d other files",
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
                platform=conda_info.get("platform"),
                path=root_path,
                environments=root_to_envs[root_path]
            )
            yield dist, unknown_files
