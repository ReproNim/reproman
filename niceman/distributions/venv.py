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
import logging
import os
import os.path as op

import attr

from six import iteritems
from niceman.distributions import Distribution
from niceman.distributions.piputils import pip_show, get_pip_packages
from niceman.dochelpers import exc_str
from niceman.utils import PathRoot, is_subpath

from .base import DistributionTracer
from .base import Package
from .base import SpecObject
from .base import TypedList

lgr = logging.getLogger("niceman.distributions.venv")


@attr.s
class VenvPackage(Package):
    name = attr.ib()
    version = attr.ib()
    local = attr.ib()
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
        pip = venv_path + "/bin/pip"
        try:
            pkgs = list(get_pip_packages(self._session, pip))
        except Exception as exc:
            lgr.warning("Could not determine pip packages for %s: %s",
                        venv_path, exc_str(exc))
            return
        return pip_show(self._session, pip, pkgs)

    def _is_venv_directory(self, path):
        try:
            self._session.execute_command(["grep", "-q", "VIRTUAL_ENV",
                                           "{}/bin/activate".format(path)])
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
            local_pkgs = set(get_pip_packages(self._session,
                                              venv_path + "/bin/pip",
                                              local_only=True))
            pkg_to_found_files = defaultdict(list)
            for path in set(unknown_files):  # Clone the set
                # The supplied path may be relative or absolute, but
                # file_to_pkg keys are absolute paths.
                fullpath = os.path.abspath(path)
                if fullpath in file_to_pkg:
                    unknown_files.remove(path)
                    pkg_to_found_files[file_to_pkg[fullpath]].append(
                        os.path.relpath(path, venv_path))

            # Some files, like venvs/dev/lib/python2.7/abc.py could be
            # symlinks populated by virtualenv itself during venv creation
            # since it relies on system wide python environment.  So we need
            # to resolve those into filenames which could be associated with
            # system wide installation of python
            for path in unknown_files.copy():
                if is_subpath(path, venv_path) and op.islink(path):
                    unknown_files.add(op.realpath(path))
                    unknown_files.remove(path)

            packages = []
            for name, details in iteritems(package_details):
                location = details["origin_location"]
                packages.append(
                    VenvPackage(name=details["name"],
                                version=details["version"],
                                local=name in local_pkgs,
                                origin_location=location,
                                files=pkg_to_found_files[name]))
                if location and not is_subpath(location, venv_path):
                    unknown_files.add(location)

            found_package_count += len(packages)

            venvs.append(
                VenvEnvironment(path=venv_path,
                                python_version=self._python_version(venv_path),
                                packages=packages))

        if venvs:
            yield (VenvDistribution(name="venv",
                                    venv_version=self._venv_version(),
                                    path=self._venv_exe_path(),
                                    environments=venvs),
                   unknown_files)

    def _python_version(self, venv_path):
        try:
            out, err = self._session.execute_command(
                [venv_path + "/bin/python", "--version"])
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
            out, _ = self._session.execute_command(["virtualenv", "--version"])
        except Exception as exc:
            lgr.debug("Could not determine virtualenv version: %s",
                      exc_str(exc))
            return
        return out.strip()

    def _venv_exe_path(self):
        try:
            out, _ = self._session.execute_command(["which", "virtualenv"])
        except Exception as exc:
            lgr.debug("Could not determine virtualenv path: %s",
                      exc_str(exc))
            return
        return out.strip()
