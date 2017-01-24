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

import os
import subprocess
from six import viewvalues
from logging import getLogger
import time


lgr = getLogger('niceman.api.retrace')


# Note: The following was derived from ReproZip's PkgManager class
# (Revised BSD License)

class PackageManager(object):
    """Base class for package identifiers."""

    def search_for_files(self, files):
        """Identifies the packages for a given collection of files

        From an iterative collection of files, we identify the packages
        that contain the files and any files that are not related.

        Parameters
        ----------
        files : array
            Iterable array of file paths

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

        for f in files:
            pkgname = self._get_package_for_file(f)

            # Stores the file
            if not pkgname:
                unknown_files.add(f)
            else:
                if pkgname in found_packages:
                    found_packages[pkgname]["files"].append(f)
                else:
                    pkg = self._create_package(pkgname)
                    if pkg:
                        found_packages[pkgname] = pkg
                        pkg["files"].append(f)
                        nb_pkg_files += 1
                    else:
                        unknown_files.add(f)

        lgr.info("%d packages with %d files, and %d other files",
                 len(found_packages),
                 nb_pkg_files,
                 len(unknown_files))

        return list(viewvalues(found_packages)), unknown_files

    def _get_package_for_file(self, filename):
        raise NotImplementedError

    def _create_package(self, pkgname):
        raise NotImplementedError


class DpkgManager(PackageManager):
    """DPKG Package Identifier
    """

    # TODO: Read in full files from dpkg/info/*.list and .config
    # TODO: (Low Priority) handle cases from dpkg-divert
    
    def _get_package_for_file(self, filename):
        return find_dpkg_for_file(filename)

    def _create_package(self, pkgname):
        try:
            with open(os.devnull, 'w') as devnull:
                r = subprocess.check_output(
                    ['dpkg-query',
                     '--showformat=${Version}\t${Installed-Size}\n',
                     '-W',
                     pkgname],
                    stderr=devnull)
        except OSError: # dpkg-query not defined
            r = ""
        except subprocess.CalledProcessError:  # Package not found
            r = ""
        if r:
            fields = r.decode().split()
            version = fields[0]
            size = int(fields[1]) * 1024    # kbytes
            pkg = {"name": pkgname,
                   "version": version,
                   "size": size,
                   "files": []}
            lgr.debug("Found package %s", pkg)
            return pkg
        else:
            return None


def find_dpkg_for_file(filename):
    """Given a file, use dpkg to identify the source package

    From the full file and pathname (given as a string), we use dpkg-query
    to identify the package that contains that file. If there is no package
    (or dpkg-query is not installed) we return an empty string.

    Parameters
    ----------
    filename : basestring
        Filename and path

    Return
    ------
    basestring
        Package name (or empty if not found)

    """
    try:
        with open(os.devnull, 'w') as devnull:
            r = subprocess.check_output(['dpkg-query', '-S', filename],
                                        stderr=devnull)
        # Note, we must split after ": " instead of ":" in case the
        # package name includes an architecture (like "zlib1g:amd64")
        pkg = r.decode().split(': ', 1)[0]
    except OSError:  # dpkg-query not defined
        pkg = ""
    except subprocess.CalledProcessError:  # Package not found
        pkg = ""
    return pkg


def identify_packages(files):
    manager = DpkgManager()
    begin = time.time()
    (packages, unknown_files) = manager.search_for_files(files)
    lgr.debug("Assigning files to packages took %f seconds",
              (time.time() - begin))

    return packages, list(unknown_files)
