# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Support for Python's virtualenv."""
from collections import defaultdict
import itertools
import logging
import os

import attr

from niceman.distributions import Distribution
from niceman.distributions.piputils import parse_pip_show, parse_pip_list
from niceman.dochelpers import exc_str
from niceman.utils import execute_command_batch, PathRoot

from .base import DistributionTracer
from .base import Package
from .base import SpecObject
from .base import TypedList

lgr = logging.getLogger("niceman.distributions.venv")


@attr.s
class VenvPackage(Package):
    name = attr.ib()
    version = attr.ib()
    origin_location = attr.ib(default=None)
    files = attr.ib(default=attr.Factory(list))


@attr.s
class VenvEnvironment(SpecObject):
    path = attr.ib(default=None)
    python_version = attr.ib(default=None)
    packages = TypedList(VenvPackage)


@attr.s
class VenvDistribution(Distribution):
    """Class to provide virtualenv-based "distributions".
    """
    path = attr.ib(default=None)
    venv_version = attr.ib(default=None)
    environments = TypedList(VenvEnvironment)

    def initiate(self, _):
        return

    def install_packages(self, session=None):
        raise NotImplementedError


class VenvTracer(DistributionTracer):
    """Distribution tracer for virtualenv.
    """

    def _init(self):
        self._path_root = PathRoot(self._is_venv_directory)

    def _get_packagefields_for_files(self, files):
        raise NotImplementedError

    def _create_package(self, **package_fields):
        raise NotImplementedError

    def _get_package_details(self, venv_path):
        packages = {}
        file_to_pkg = {}

        pkgs, locs = map(list, zip(*self._pip_packages(venv_path)))
        batch = execute_command_batch(self._session,
                                      [venv_path + "/bin/pip", "show", "-f"],
                                      pkgs)
        entries = (stacked.split("---") for stacked, _, _ in batch)

        for pkg, loc, entry in zip(pkgs, locs, itertools.chain(*entries)):
            info = parse_pip_show(entry)
            details = {"name": info["Name"],
                       "version": info["Version"],
                       "location": loc}
            packages[pkg] = details
            for path in info["Files"]:
                full_path = os.path.normpath(
                    os.path.join(info["Location"], path))
                file_to_pkg[full_path] = pkg
        return packages, file_to_pkg

    def _is_venv_directory(self, path):
        try:
            self._session.execute_command("grep -q VIRTUAL_ENV "
                                          "{}/bin/activate".format(path))
        except Exception as exc:
            lgr.debug("Did not detect virtualenv at the path %s: %s",
                      path, exc_str(exc))
            return False
        return True

    def _get_venv_path(self, path):
        return self._path_root(path)

    def identify_distributions(self, files):
        unknown_files = set(files)
        found_package_count = 0
        total_file_count = len(unknown_files)

        venv_paths = map(self._get_venv_path, files)
        venv_paths = set(filter(None, venv_paths))

        venvs = []
        for venv_path in venv_paths:
            package_details, file_to_pkg = self._get_package_details(venv_path)
            pkg_to_found_files = defaultdict(list)
            for path in set(unknown_files):  # Clone the set
                if path in file_to_pkg:
                    unknown_files.remove(path)
                    pkg_to_found_files[file_to_pkg[path]].append(
                        os.path.relpath(path, venv_path))

            packages = [VenvPackage(name=details["name"],
                                    version=details["version"],
                                    origin_location=details["location"],
                                    files=pkg_to_found_files[name])
                        for name, details in package_details.items()]

            found_package_count += len(packages)

            venvs.append(
                VenvEnvironment(path=venv_path,
                                python_version=self._python_version(venv_path),
                                packages=packages))

        lgr.info("%s: %d packages with %d files, and %d other files",
                 self.__class__.__name__,
                 found_package_count,
                 total_file_count - len(unknown_files),
                 len(unknown_files))

        if venvs:
            yield (VenvDistribution(name="venv",
                                    venv_version=self._venv_version(),
                                    path=self._venv_exe_path(),
                                    environments=venvs),
                   list(unknown_files))

    def _pip_packages(self, venv_path):
        # We could use either 'pip list' or 'pip freeze' to get a list
        # of packages.  The choice to use 'list' rather than 'freeze'
        # is based on how they show editable packages.  'list' outputs
        # a source directory of the package, whereas 'freeze' outputs
        # a URL like "-e git+https://github.com/[...]".
        #
        # It would be nice to use 'pip list --format=json' rather than
        # the legacy format.  However, currently (pip 9.0.1, 2018/01),
        # the json format does not include location information for
        # editable packages (though it is supported in a developmental
        # version).
        try:
            out, _ = self._session.execute_command([venv_path + "/bin/pip",
                                                    "list", "--format=legacy"])

        except Exception as exc:
            lgr.warning("Could determine pip packages for %s: %s",
                        venv_path, exc_str(exc))
            return
        for pkg, _, loc in parse_pip_list(out):
            yield pkg, loc

    def _python_version(self, venv_path):
        try:
            out, err = self._session.execute_command(
                venv_path + "/bin/python --version")
            # Python 2 sends its version to stderr, while Python 3
            # sends it to stdout.  Version has format "Python
            pyver = out if "Python" in out else err
            return pyver.strip().split()[1]
        except Exception as exc:
            lgr.debug("Could not determine python version: %s",
                      exc_str(exc))
            return

    # A virtualenv directory doesn't contain any information about
    # which virtualenv created it, so we just go with its current
    # version and location.

    def _venv_version(self):
        try:
            out, _ = self._session.execute_command("virtualenv --version")
        except Exception as exc:
            lgr.debug("Could not determine virtualenv version: %s",
                      exc_str(exc))
            return
        return out.strip()

    def _venv_exe_path(self):
        try:
            out, _ = self._session.execute_command("which virtualenv")
        except Exception as exc:
            lgr.debug("Could not determine virtualenv path: %s",
                      exc_str(exc))
            return
        return out.strip()
