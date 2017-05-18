# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrators helping with management of target environments (remote or local)"""

import os
import abc

from importlib import import_module
from six import viewvalues

from niceman.cmd import Runner

import logging
lgr = logging.getLogger('niceman.distributions')


class Distribution(object):
    """
    Base class for providing distribution-based shell commands.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, provenance):
        """
        Class constructor

        Parameters
        ----------
        provenance : object
            Provenance class instance
        """
        self._provenance = provenance

    @staticmethod
    def factory(distribution_type, provenance):
        """
        Factory method for creating the appropriate Orchestrator sub-class
        based on format type.

        Parameters
        ----------
        distribution_type : string
            Type of distribution subclass to create. Current options are:
            'conda', 'debian', 'neurodebian', 'pypi'
        provenance : object
            Provenance class instance.

        Returns
        -------
        distribution : object
            Instance of a Distribution sub-class
        """
        class_name = distribution_type.capitalize() + 'Distribution'
        module = import_module('niceman.distributions.' + distribution_type)
        return getattr(module, class_name)(provenance)

    @abc.abstractmethod
    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        return

    @abc.abstractmethod
    def install_packages(self, environment):
        """
        Install the packages associated to this distribution by the provenance
        into the environment.

        Parameters
        ----------
        environment : object
            Environment sub-class instance.
        """
        return

# Note: The following was derived from ReproZip's PkgManager class
# (Revised BSD License)

class PackageTracer(object):
    """Base class for package trackers.

    ATM :term:`Package` describes all of possible "archives" which deliver
    some piece of software or data -- packages by distributions (Debian, conda,
    pip, ...), VCS repositories or even container images -- something which has
    to be installed to fulfill environment spec
    """

    def __init__(self, environ=None):
        # will be (re)used to run external commands, and let's hardcode LC_ALL
        # codepage just in case since we might want to comprehend error
        # messages
        self._environ = environ or Runner(env={'LC_ALL': 'C'})

    def identify_packages_from_files(self, files):
        """Identifies packages for a given collection of files

        From an iterative collection of files, we identify the packages
        that contain the files and any files that are not related.

        Parameters
        ----------
        files : iterable
            Container (e.g. list or set) of file paths

        Return
        ------
        (found_packages, unknown_files)
            - found_packages is a list of dicts that holds information about
              the found packages. Package dicts need at least "name" and
              "files" (that contains an array of related files)
            - unknown_files is a list of files that were not found in
              a package
        """
        unknown_files = set()
        found_packages = {}
        nb_pkg_files = 0

        file_to_package_dict = self._get_packagenames_for_files(files)
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

    def _get_packagenames_for_files(self, files):
        raise NotImplementedError

    def _create_package(self, pkgname):
        """Creates implementation specific Package object

        (well -- atm still an OrderedDict)
        """
        raise NotImplementedError
