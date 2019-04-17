# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Support for Python's virtualenv."""
from collections import defaultdict
import logging
import os
import os.path as op

import attr

from reproman.distributions import Distribution
from reproman.distributions import piputils
from reproman.dochelpers import borrowdoc
from reproman.dochelpers import exc_str
from reproman.utils import attrib, PathRoot, is_subpath
from reproman.utils import execute_command_batch
from reproman.utils import parse_semantic_version
from reproman.resource.session import get_local_session

from .base import DistributionTracer
from .base import Package
from .base import SpecObject
from .base import TypedList

lgr = logging.getLogger("reproman.distributions.venv")


@attr.s
class VenvPackage(Package):
    name = attrib(default=attr.NOTHING)
    version = attrib(default=attr.NOTHING)
    local = attrib(default=False)
    location = attrib()
    editable = attrib(default=False)
    files = attrib(default=attr.Factory(list))
    _diff_cmp_fields = ('name', )
    _diff_fields = ('version', )


@attr.s
class VenvEnvironment(SpecObject):
    path = attrib()
    python_version = attrib()
    packages = TypedList(VenvPackage)
    _diff_cmp_fields = ('path', 'python_version')
    _collection_attribute = 'packages'


@attr.s
class VenvDistribution(Distribution):
    """Class to provide virtualenv-based "distributions".
    """
    path = attrib()
    venv_version = attrib()
    environments = TypedList(VenvEnvironment)
    _collection_attribute = 'environments'

    def initiate(self, _):
        return

    @borrowdoc(Distribution)
    def install_packages(self, session=None):
        session = session or get_local_session()
        for env in self.environments:
            # TODO: Deal with system and editable packages.
            to_install = ["{p.name}=={p.version}".format(p=p)
                          for p in env.packages
                          if p.local and not p.editable]
            if not to_install:
                lgr.info("No local, non-editable packages found")
                continue

            # TODO: Right now we just use the python to invoke "virtualenv
            # --python=..." when the directory doesn't exist, but we should
            # eventually use the yet-to-exist "satisfies" functionality to
            # check whether an existing virtual environment has the right
            # python (and maybe other things).
            pyver = "{v.major}.{v.minor}".format(
                v=parse_semantic_version(env.python_version))

            if not session.exists(env.path):
                # The location and version of virtualenv are recorded at the
                # time of tracing, but should we use these values?  For now,
                # use a plain "virtualenv" below on the basis that we just use
                # "apt-get" and "git" elsewhere.
                session.execute_command(["virtualenv",
                                         "--python=python{}".format(pyver),
                                         env.path])
            list(execute_command_batch(session,
                                       [env.path + "/bin/pip", "install"],
                                       to_install))


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
            packages, file_to_pkg = piputils.get_package_details(
                self._session, pip)
        except Exception as exc:
            lgr.warning("Could not determine pip package details for %s: %s",
                        venv_path, exc_str(exc))
            return {}, {}
        return packages, file_to_pkg

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

        venv_paths = map(self._get_venv_path, files)
        venv_paths = set(filter(None, venv_paths))

        venvs = []
        for venv_path in venv_paths:
            package_details, file_to_pkg = self._get_package_details(venv_path)
            local_pkgs = set(piputils.get_pip_packages(self._session,
                                                       venv_path + "/bin/pip",
                                                       restriction="local"))
            pkg_to_found_files = defaultdict(list)
            for path in set(unknown_files):  # Clone the set
                # The supplied path may be relative or absolute, but
                # file_to_pkg keys are absolute paths.
                fullpath = os.path.abspath(path)
                if fullpath in file_to_pkg:
                    unknown_files.remove(path)
                    pkg_to_found_files[file_to_pkg[fullpath]].append(
                        os.path.relpath(path, venv_path))

            # Some virtualenv files are links to system files. Files themselves
            # may be linked or they may be in a linked directory. We need to
            # resolve these links and pass them out as unknown files for other
            # tracers to use.
            for path in unknown_files.copy():
                if is_subpath(path, venv_path):
                    rpath = op.realpath(path)
                    # ... but the resolved link may point to another path under
                    # the environment (e.g., bin/python -> bin/python3), and we
                    # don't want to pass that back out as unknown.
                    if not is_subpath(rpath, venv_path):
                        unknown_files.add(rpath)
                    unknown_files.remove(path)

            packages = []
            for name, details in package_details.items():
                location = details["location"]
                packages.append(
                    VenvPackage(name=details["name"],
                                version=details["version"],
                                local=name in local_pkgs,
                                location=location,
                                editable=details["editable"],
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
            # sends it to stdout.
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
