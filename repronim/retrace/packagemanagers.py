# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to identify package sources for files"""

from __future__ import unicode_literals
from six import iteritems, viewvalues
from logging import getLogger

import time
from rpaths import Path
import subprocess
lgr = getLogger('repronim.api.retrace')


# Note: The following was derived from ReproZip's PkgManager class
# (Revised BSD License)

class PackageManager(object):
    """Base class for package identifiers."""
    def __init__(self):
        # Files that were not part of a package
        self.unknown_files = set()
        # All the packages identified, with their `files` attribute set
        self.packages = {}

    def search_for_files(self, files):
        nb_pkg_files = 0

        for f in files:
            pkgnames = self._get_packages_for_file(f)

            # Stores the file
            if not pkgnames:
                self.unknown_files.add(f)
            else:
                pkgs = []
                for pkgname in pkgnames:
                    if pkgname in self.packages:
                        pkgs.append(self.packages[pkgname])
                    else:
                        pkg = self._create_package(pkgname)
                        if pkg is not None:
                            self.packages[pkgname] = pkg
                            pkgs.append(self.packages[pkgname])
                if len(pkgs) == 1:
                    pkgs[0].add_file(f)
                    nb_pkg_files += 1
                else:
                    self.unknown_files.add(f)

        # Filter out packages with no files
        self.packages = {pkgname: pkg
                         for pkgname, pkg in iteritems(self.packages)
                         if pkg.files}

        lgr.info("%d packages with %d files, and %d other files",
                 len(self.packages),
                 nb_pkg_files,
                 len(self.unknown_files))

    def _get_packages_for_file(self, filename):
        raise NotImplementedError

    def _create_package(self, pkgname):
        raise NotImplementedError


class DpkgManager(PackageManager):
    """DPKG Package Identifier
    """

    def search_for_files(self, files):
        # Make a set of all the requested files
        requested = dict((f, f) for f in files)
        found = {}  # {path: pkgname}

        # Process /var/lib/dpkg/info/*.list
        # TODO: Also search .conffiles
        for listfile in Path('/var/lib/dpkg/info').listdir():
            pkgname = listfile.unicodename[:-5]
            # Removes :arch
            pkgname = pkgname.split(':', 1)[0]

            if not listfile.unicodename.endswith('.list'):
                continue
            with listfile.open('rb') as fp:
                # Read paths from the file
                l = fp.readline()
                while l:
                    if l[-1:] == b'\n':
                        l = l[:-1]
                    path = Path(l)
                    # If it's one of the requested paths
                    if path in requested:
                        # If we had assigned it to a package already, undo
                        if path in found:
                            found[path] = None
                        # Else assign to the package
                        else:
                            found[path] = pkgname
                    l = fp.readline()

        # Remaining files are not from packages
        self.unknown_files.update(
            f for f in files
            if f in requested and found.get(f) is None)

        nb_pkg_files = 0

        for path, pkgname in iteritems(found):
            if pkgname is None:
                continue
            if pkgname in self.packages:
                package = self.packages[pkgname]
            else:
                package = self._create_package(pkgname)
                self.packages[pkgname] = package
            package["files"].append(requested.pop(path))
            nb_pkg_files += 1

        lgr.info("%d packages with %d files, and %d other files",
                 len(self.packages),
                 nb_pkg_files,
                 len(self.unknown_files))

    def _get_packages_for_file(self, filename):
        # This method is no longer used for dpkg: instead of querying each file
        # using `dpkg -S`, we read all the list files once ourselves since it
        # is faster
        assert False

    def _create_package(self, pkgname):
        p = subprocess.Popen(['dpkg-query',
                              '--showformat=${Package}\t'
                              '${Version}\t'
                              '${Installed-Size}\n',
                              '-W',
                              pkgname],
                             stdout=subprocess.PIPE)
        try:
            size = version = None
            for l in p.stdout:
                fields = l.split()
                # Removes :arch
                name = fields[0].decode('ascii').split(':', 1)[0]
                if name == pkgname:
                    version = fields[1].decode('ascii')
                    size = int(fields[2].decode('ascii')) * 1024    # kbytes
                    break
            for l in p.stdout:  # finish draining stdout
                pass
        finally:
            p.wait()
        if p.returncode == 0:
            pkg = {"name": pkgname,
                   "version": version,
                   "size": size,
                   "files": []}
            lgr.debug("Found package %s", pkg)
            return pkg
        else:
            return None


def identify_packages(files):
    manager = DpkgManager()
    begin = time.time()
    manager.search_for_files(files)
    lgr.debug("Assigning files to packages took %f seconds",
              (time.time() - begin))

    return manager.unknown_files, list(viewvalues(manager.packages))
