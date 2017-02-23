# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to identify package sources for files"""

from __future__ import unicode_literals

import collections
import os
from os.path import join as opj
import time

from os.path import dirname, isdir, isabs
from os.path import exists, lexists
from os.path import join as opj

from logging import getLogger
from six import viewvalues
from six.moves.urllib.parse import urlparse

import pytz
from datetime import datetime

from niceman.dochelpers import exc_str
import niceman.utils as utils
from niceman.support.exceptions import MultipleReleaseFileMatch

try:
    import apt
    import apt.utils as apt_utils
    import apt_pkg
    cache = apt.Cache()
except ImportError:
    apt = None
    apt_utils = None
    apt_pkg = None
    cache = None

from niceman.cmd import Runner
from niceman.cmd import CommandError

lgr = getLogger('niceman.api.retrace')

# Pick a conservative max command-line
try:
    _MAX_LEN_CMDLINE = os.sysconf(str("SC_ARG_MAX")) // 2
except ValueError:
    _MAX_LEN_CMDLINE = 2048

# Note: The following was derived from ReproZip's PkgManager class
# (Revised BSD License)


# TODO:  we might want to rename
#  Package ...
#  Manager -> Resolver?  since we are trying to resolve paths into their
#             corresponding "Package"s
class PackageManager(object):
    """Base class for package identifiers.

    ATM :term:`Package` describes all of possible "containers" which deliver
    some piece of software or data -- packages by distributions (Debian, conda,
    pip, ...) or VCS repositories"""

    def __init__(self):
        # will be (re)used to run external commands, and let's hardcode LC_ALL
        # codepage just in case since we might want to comprehend error
        # messages
        self._runner = Runner(env={'LC_ALL': 'C'})

    def search_for_files(self, files):
        """Identifies the packages for a given collection of files

        From an iterative collection of files, we identify the packages
        that contain the files and any files that are not related.

        Parameters
        ----------
        files : iterable
            Container (e.g. list or set) of file paths

        Return
        ------
        (found_packages, unknown_files)
            - found_packages is an array of dicts that holds information about
              the found packages. Package dicts need at least "name" and
              "files" (that contains an array of related files)
            - unknown_files is a list of files that were not found in
              a package
        """
        unknown_files = set()
        found_packages = {}
        nb_pkg_files = 0

        file_to_package_dict = self._get_packages_for_files(files)
        for f in files:
            if not os.path.lexists(f):
                lgr.warning(
                    "Provided file %s doesn't exist, spec might be incomplete",
                    f)
            # Stores the file
            if f not in file_to_package_dict:
                unknown_files.add(f)
            else:
                # TODO: pkgname should become  pkgid
                # where for packages from distributions would be name,
                # for VCS -- their path
                pkgname = file_to_package_dict[f]
                if pkgname is None:
                    unknown_files.add(f)
                elif pkgname in found_packages:
                    found_packages[pkgname]["files"].append(f)
                    nb_pkg_files += 1
                else:
                    pkg = self._create_package(pkgname)
                    if pkg:
                        found_packages[pkgname] = pkg
                        pkg["files"].append(f)
                        nb_pkg_files += 1
                    else:
                        unknown_files.add(f)

        lgr.info("%s: %d packages with %d files, and %d other files",
                 self.__class__.__name__,
                 len(found_packages),
                 nb_pkg_files,
                 len(unknown_files))

        return list(viewvalues(found_packages)), list(unknown_files)

    def identify_package_origins(self, packages):
        """Identify and collate origins from a set of packages

        From a collection of packages, identify the unique origins
        into a separate collection.

        Parameters
        ----------
        packages : iterable
            Array of Package (to be updated)

        Return
        ------
        (origins)
            - Discovered collection of origins
        """
        raise NotImplementedError

    def _get_packages_for_files(self, filename):
        raise NotImplementedError

    def _create_package(self, pkgname):
        raise NotImplementedError


class DpkgManager(PackageManager):
    """DPKG Package Identifier
    """

    # TODO: (Low Priority) handle cases from dpkg-divert

    def identify_package_origins(self, packages):
        used_names = set()  # Set to avoid duplicate origin names
        origin_map = {}  # Map original origins to the yaml-prepared origins

        # Iterate over all package origins
        for p in packages:
            for v in p.get("version_table", []):
                for i, o in enumerate(v.get("origins", [])):
                    o = utils.HashableDict(o)
                    # If we haven't seen this origin before, generate it
                    if o not in origin_map:
                        origin_map[o] = self._create_origin(o, used_names)
                    # Now replace the package origin with the name of the
                    # yaml-prepared origin
                    v["origins"][i] = origin_map[o]["name"]

        # Sort the origins by the name for the configuration file
        origins = sorted(origin_map.values(), key=lambda k: k["name"])

        return origins

    @staticmethod
    def _create_origin(o, used_names):
        # Create a unique name for the origin
        name_fmt = "apt_%s_%s_%s_%%d" % (o.get("origin"), o.get("archive"),
                                         o.get("component"))
        name = utils.generate_unique_name(name_fmt,
                                          used_names)
        # Remember the created name
        used_names.add(name)
        # Create a new ordered dictionary to be used in the config file
        new_o = collections.OrderedDict()
        new_o["name"] = name
        new_o["type"] = "apt"
        new_o.update(o)
        return new_o

    def _get_packages_for_files(self, files):
        file_to_package_dict = {}

        # Find out how many files we can query at once
        max_len = max([len(f) for f in files])
        num_files = max((_MAX_LEN_CMDLINE - 13) // (max_len + 1), 1)

        for subfiles in (files[pos:pos + num_files]
                         for pos in range(0, len(files), num_files)):
            try:
                out, err = self._runner.run(
                    ['dpkg-query', '-S'] + subfiles,
                    expect_stderr=True, expect_fail=True
                )
            except CommandError as exc:
                if 'no path found matching pattern' in exc.stderr:
                    out = exc.stdout  # One file not found, so continue
                else:
                    raise  # some other fault -- handle it above
            # Decode output for Python 2
            try:
                out = out.decode()
            except AttributeError:
                pass

            # Now go through the output and assign packages to files
            for outline in out.splitlines():
                # Note, we must split after ": " instead of ":" in case the
                # package name includes an architecture (like "zlib1g:amd64")
                # TODO: Handle query of /bin/sh better
                (pkg, found_name) = outline.split(': ', 1)
                lgr.debug("Identified file %r to belong to package %s",
                          found_name, pkg)
                file_to_package_dict[found_name] = pkg

        return file_to_package_dict

    def _create_package(self, pkgname):
        if not cache:
            return None
        try:
            pkg_info = cache[pkgname]
        except KeyError:  # Package not found
            return None

        # prep our pkg object:
        pkg = collections.OrderedDict()
        pkg["name"] = pkgname
        pkg["type"] = "dpkg"
        pkg["version"] = pkg_info.installed.version
        pkg["candidate"] = pkg_info.candidate.version
        pkg["size"] = pkg_info.installed.size
        pkg["architecture"] = pkg_info.installed.architecture
        pkg["md5"] = pkg_info.installed.md5
        pkg["sha1"] = pkg_info.installed.sha1
        pkg["sha256"] = pkg_info.installed.sha256
        if pkg_info.installed.source_name:
            pkg["source_name"] = pkg_info.installed.source_name
            pkg["source_version"] = pkg_info.installed.source_version
        pkg["files"] = []

        # Now get installation date
        try:
            pkg["install_date"] = str(
                pytz.utc.localize(
                    datetime.utcfromtimestamp(
                        os.path.getmtime(
                            "/var/lib/dpkg/info/" + pkgname + ".list"))))
        except OSError:  # file not found
            pass

        # Compile Version Table
        pkg_versions = []
        for v in pkg_info.versions:
            v_info = {"version": v.version}
            origins = []
            for o in v.origins:
                origin = {"component": o.component,
                          "archive": o.archive,
                          "origin": o.origin,
                          "label": o.label,
                          "site": o.site}
                # Get the release date
                rdate = self._find_release_date(o.site, o.archive)
                if rdate:
                    origin["date"] = rdate
                # Now add our crafted origin to the list
                origins.append(origin)
            v_info["origins"] = origins
            pkg_versions.append(v_info)

        pkg["version_table"] = pkg_versions

        lgr.debug("Found package %s", pkg)
        return pkg

    def _find_release_date(self, site, archive):
        if not site:
            return None
        # First find the release file
        # This uses logic similar to apt.utils.get_release_filename_for_pkg
        # but restricts matches to the source site
        rfile = None
        dirname = apt_pkg.config.find_dir("Dir::State::lists")
        # If we want to avoid using cache._list, we can call
        # apt_pkg.SourceList() directly
        for uri in set([metaindex.uri for metaindex in cache._list.list]):
            if site == urlparse(uri).netloc:
                for relfile in ['InRelease', 'Release']:
                    name = ((apt_pkg.uri_to_filename(uri)) +
                            "dists_%s_%s" % (archive, relfile))
                    if os.path.exists(opj(dirname, name)):
                        if rfile:
                            raise MultipleReleaseFileMatch(
                                "More than one release file found for %s %s" %
                                (site, archive))
                        rfile = opj(dirname, name)

        # Now extract and format the date from the release file
        rdate = None
        if rfile:
            rdate = apt_utils.get_release_date_from_release_file(rfile)
            if rdate:
                rdate = str(pytz.utc.localize(
                    datetime.utcfromtimestamp(rdate)))
        return rdate


def identify_packages(files):
    """Identify packages files belong to

    Parameters
    ----------
    files : iterable
      Files to consider

    Returns
    -------
    packages : list of Package
    origins : list of Origin
    unknown_files : list of str
      Files which were not determined to belong to some package
    """
    # TODO: move this function into the base.py having decided on naming etc
    from .vcs import VCSManager
    managers = [DpkgManager(), VCSManager()]
    origins = []
    packages = []

    files_to_consider = files

    for manager in managers:
        begin = time.time()
        (packages_, unknown_files) = manager.search_for_files(files_to_consider)
        packages_origins = manager.identify_package_origins(packages_)
        if packages_origins:
            origins += packages_origins
        lgr.debug("Assigning files to packages by %s took %f seconds",
                  manager, time.time() - begin)
        packages += packages_
        files_to_consider = unknown_files

    return packages, origins, files_to_consider
