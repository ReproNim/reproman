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
import attr
import collections
import yaml

from importlib import import_module
from six import viewvalues

from niceman.resource.session import get_local_session

import logging
lgr = logging.getLogger('niceman.distributions')


Factory = attr.Factory


def TypedList(type_):
    """A helper to generate an attribute which would be with list factory 
    but also defining a type in its metadata
    """
    return attr.ib(default=Factory(list), metadata={'type': type_})


#
# Models
#

class SpecObject(object):
    @staticmethod
    def yaml_representer(dumper, data):

        ordered_items = filter(
            lambda i: bool(i[1]),  # so only non empty/None
            attr.asdict(
                data, dict_factory=collections.OrderedDict).items())
        return dumper.represent_mapping('tag:yaml.org,2002:map', ordered_items)


def _register_with_representer(cls):
    # TODO: check if we could/should just inherit from  yaml.YAMLObject
    # or could may be craft our own metaclass
    yaml.SafeDumper.add_representer(cls, SpecObject.yaml_representer)


@attr.s
class Package(SpecObject):
    # files used/associated with the package
    # Unfortunately cannot be the one with default value in the super-class :-/
    # https://github.com/python-attrs/attrs/issues/38
    # So for now will be defined specifically per each subclass
    # files = attr.ib(default=attr.Factory(list))
    pass


@attr.s
class Distribution(SpecObject):
    """Base class for distributions"""

    __metaclass__ = abc.ABCMeta

    # Actually might want/need to go away since somewhat duplicates the class
    # name and looks awkward
    name = attr.ib()

    @staticmethod
    def factory(distribution_type, provenance=None):
        """
        Factory method for creating the appropriate Orchestrator sub-class
        based on format type.

        Parameters
        ----------
        distribution_type : string
            Type of distribution subclass to create. Current options are:
            'conda', 'debian', 'neurodebian', 'pypi'
        provenance : dict
            Keyword args to be passed to initialize class instance 

        Returns
        -------
        distribution : object
            Distribution class or its instance (when provenance is not None)
        """
        class_name = distribution_type.capitalize() + 'Distribution'
        module = import_module('niceman.distributions.' + distribution_type.lower())
        class_ = getattr(module, class_name)
        return class_ if provenance is None else class_(**provenance)

    @abc.abstractmethod
    def initiate(self, session):
        """
        Perform any initialization commands needed in the environment environment.

        Parameters
        ----------
        session : object
            The Session to work in
        """
        return

    @abc.abstractmethod
    def install_packages(self, session=None):
        """
        Install the packages associated to this distribution by the provenance
        into the environment.

        Parameters
        ----------
        session : object
            Session to work in
        """
        return

# So this one is no longer "distributions/" module specific
# TODO: move up! and strip Spec suffix
@attr.s
class EnvironmentSpec(SpecObject):
    base = attr.ib(default=None)  # ???  to define specifics of the system, possibly a docker base
    distributions = TypedList(Distribution)  # list of distributions
    files = attr.ib(default=Factory(list))  # list of other files
    # runs?  whenever we get to provisioning executions
    #        those would also be useful for tracing for presence of distributions
    #        e.g. depending on what is in the PATH

_register_with_representer(EnvironmentSpec)


# Note: The following was derived from ReproZip's PkgManager class
# (Revised BSD License)

class DistributionTracer(object):
    """Base class for package trackers.

    ATM :term:`Package` describes all of possible "archives" which deliver
    some piece of software or data -- packages by distributions (Debian, conda,
    pip, ...), VCS repositories or even container images -- something which has
    to be installed to fulfill environment spec
    """

    __metaclass__ = abc.ABCMeta

    # Default to being able to handle directories
    HANDLES_DIRS = True

    def __init__(self, session=None):
        # will be (re)used to run external commands, and let's hardcode LC_ALL
        # codepage just in case since we might want to comprehend error
        # messages
        self._session = session or get_local_session()
        # to ease _init within derived classes which should not be parametrized
        # more anyways
        self._init()

    def _init(self):
        pass

    @abc.abstractmethod
    def identify_distributions(self, files):
        raise NotImplementedError()

    # This one assumes that distribution works with "packages"
    # TODO: we might want to create a more specialized sub-class for that purpose
    # and move those methods below into that subclass
    # TODO: moreover this one assumes only detection by the files and
    #       provides a generic implementation which is based on stages:
    #       1. for each file identifying package fields uniquely describing the
    #          package (method `_get_packagefields_for_files`)
    #       2. groupping fields based on the packagefields
    #       3. creating an actual `Package` using those fields for each group
    #          of files.
    #  In principle could be RFed to be more scalable, where there is a "Package
    #  manager", which provides similar "assign file to a package" functionality
    #  and identifying packages as already known to the manager.
    def identify_packages_from_files(self, files):
        """Identifies "packages" for a given collection of files

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

        # TODO: probably that _get_packagefields should create packagespecs
        # internally and just return them.  But we should make them hashable
        file_to_package_dict = self._get_packagefields_for_files(files)
        for f in files:
            # Stores the file
            if f not in file_to_package_dict:
                unknown_files.add(f)
            else:
                # TODO: pkgname should become  pkgid
                # where for packages from distributions would be name,
                # for VCS -- their path
                pkgfields = file_to_package_dict[f]
                if pkgfields is None:
                    unknown_files.add(f)
                else:
                    pkgfields_hashable = tuple(x for x in pkgfields.items())
                    if pkgfields_hashable in found_packages:
                        found_packages[pkgfields_hashable].files.append(f)
                        nb_pkg_files += 1
                    else:
                        pkg = self._create_package(**pkgfields)
                        if pkg:
                            found_packages[pkgfields_hashable] = pkg
                            # we store only non-directories within 'files'
                            if not self._session.isdir(f):
                                pkg.files.append(f)
                            nb_pkg_files += 1
                        else:
                            unknown_files.add(f)

        lgr.info("%s: %d packages with %d files, and %d other files",
                 self.__class__.__name__,
                 len(found_packages),
                 nb_pkg_files,
                 len(unknown_files))

        return list(viewvalues(found_packages)), list(unknown_files)

    @abc.abstractmethod
    def _get_packagefields_for_files(self, files):
        """Given a list of files, should return a dict mapping files to a
        dictionary of fields which would be later passed into _create_package
        to actually create packages while groupping into packages 
        (having identical returned packagefield values)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _create_package(self, **package_fields):
        """Creates implementation-specific Package object using fields
        provided by _get_packagefields_for_files
        """
        raise NotImplementedError
