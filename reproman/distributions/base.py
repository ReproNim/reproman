# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrators helping with management of target environments (remote or local)"""

import os.path as op
import abc
import attr
import collections
import yaml

from importlib import import_module

from reproman.utils import attrib
from reproman.resource.session import get_local_session

import logging
lgr = logging.getLogger('reproman.distributions')


Factory = attr.Factory


def TypedList(type_):
    """A helper to generate an attribute which would be with list factory 
    but also defining a type in its metadata
    """
    return attrib(default=Factory(list), metadata={'type': type_})


#
# Models
#

class SpecObject(object):

    # TODO: make sure these can't stay empty in subclasses where they are 
    # needed (or make sure the trivial case is handled)

    # Fields used to establish the "identity" of the specobject for the 
    # purposes of diff
    _diff_cmp_fields = tuple()
    # Fields of the primary interest when showing diff
    _diff_fields = tuple()

    @property
    def _diff_cmp_id(self):
        if not self._diff_cmp_fields:
            # Might need to be gone or some custom exception
            raise RuntimeError(
                "Cannot establish identity of %r since _diff_cmp_fields "
                "are not defined" % self)
        return tuple(getattr(self, a) for a in self._diff_cmp_fields)

    @property
    def _cmp_id(self):
        if not self._diff_cmp_fields:
            # Might need to be gone or some custom exception
            raise RuntimeError(
                "Cannot establish identity of %r since _diff_cmp_fields "
                "are not defined" % self)
        if not self._diff_fields:
            # Might need to be gone or some custom exception
            raise RuntimeError(
                "Cannot establish identity of %r since _diff_fields "
                "are not defined" % self)
        vals = [ getattr(self, a) for a in self._diff_cmp_fields ]
        vals.extend([ getattr(self, a) for a in self._diff_fields ])
        return tuple(vals)

    @property
    def _diff_vals(self):
        """gives the values of the attributes defined by _diff_fields (like 
        _diff_cmp_id for _diff_cmp_fields)
        """
        return tuple(str(getattr(self, a)) for a in self._diff_fields)

    @property
    def diff_identity_string(self):
        """a string describing the identity of the object

        this can be overridden if there's a nicer way of expressing the 
        identity than just stringing the identity keys togeter (e.g. for 
        a VCS repository identified by an opaque string, we can include 
        the path of the repository)
        """
        return " ".join(str(el) for el in self._diff_cmp_id if el is not None)

    @property
    def diff_subidentity_string(self):
        """like diff_identity_string, but to distinguish objects that have 
        matching _diff_cmp_fields
        """
        return " ".join(str(el) for el in self._diff_vals if el is not None)

    @property
    def identity_string(self):
        """like diff_identity_string, but for both _diff_cmp_fields and 
        _diff_fields (used in satisfied_by comparisons)
        """
        return " ".join(str(el) for el in self._cmp_id if el is not None)

    # TODO: make it "lazy" or may be there is already a helper in attrs?
    @property
    def _attr_names(self):
        return tuple(f.name for f in self.__attrs_attrs__)


    # For SpecObjects that act as containers for other SpecObjects that
    # provide the functionality (e.g. DebianDistributions that contains
    # DEBPackages), _collection is the attribute that acts as the sequence 
    # holding the contained SpecObjects.
    @property
    def collection(self):
        return getattr(self, self._collection_attribute)


    @staticmethod
    def yaml_representer(dumper, data):

        ordered_items = filter(
            lambda i: bool(i[1]),  # so only non empty/None
            attr.asdict(
                data, dict_factory=collections.OrderedDict).items())
        return dumper.represent_mapping('tag:yaml.org,2002:map', ordered_items)


    def compare(self, other, mode):
        if mode == 'satisfied_by':
            return self._satisfied_by(other)
        if mode == 'identical_to':
            return self._identical_to(other)
        raise ValueError('bad value for mode')


    def _satisfied_by(self, other):
        """Determine if the other object satisfies the requirements of this 
        spec object.

        We require that the values of the attributes given by 
        _diff_cmp_fields and _diff_fields are the same.  A specobject 
        with a value of None for one of these attributes is less specific 
        than one with a specific value; the former cannot satisfy the 
        latter, but the latter can satisfy the former.

        TODO: Ensure we don't encounter the case where self is completely 
        unspecified (all values are None), in which case satisfied_by() 
        returns True by default.  Perhaps this is done by making 
        sure that at least one of the _diff_cmp_fields cannot be None.

        TODO: derive _collection_type directly from _collection.  This isn't 
        possible at the moment because DebianDistribution.packages is 
        overwritten at some point and emerges here (in staisfies()) as a 
        list.  We have to go back to the definition of packages in the 
        DebianDistribution class (not an object) to find the type.
        """
        if hasattr(other, 'collection'):
            if hasattr(self, 'collection'):
                return all(obj.compare(other, mode='satisfied_by') for obj in self.collection)
            other_collection_type = getattr(other.__class__.__attrs_attrs__, other._collection_attribute).metadata['type']
            if isinstance(self, other_collection_type):
                return any(self.compare(obj, mode='satisfied_by') for obj in other.collection)
            raise TypeError('don''t know how to determine if a %s is satisfied by a %s' % (self.__class__, other_collection_type))
        if not isinstance(other, self.__class__):
            raise TypeError('incompatible specobject types')
        for (self_value, other_value) in zip(self._cmp_id, other._cmp_id):
            if self_value is None:
                continue
            if self_value != other_value:
                return False
        return True


    def _identical_to(self, other):
        """Determine if the other object is identical to the spec object.

        We require that the objects are of the same type and that the 
        values of the attributes given by _diff_cmp_fields and _diff_fields 
        (dereferenced in _cmp_id) are the same.
        """
        if not isinstance(other, self.__class__):
            return False
        return all(sv==ov for sv, ov in zip(self._cmp_id, other._cmp_id))


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
class Distribution(SpecObject, metaclass=abc.ABCMeta):
    """Base class for distributions"""

    # Actually might want/need to go away since somewhat duplicates the class
    # name and looks awkward
    name = attrib(default=attr.NOTHING)

    @staticmethod
    def factory(distribution_type, provenance=None):
        """
        Factory method for creating the appropriate Orchestrator sub-class
        based on format type.

        Parameters
        ----------
        distribution_type : string
            Type of distribution subclass to create. Current options are:
            'conda', 'debian', 'neurodebian', 'pypi', 'redhat'
        provenance : dict
            Keyword args to be passed to initialize class instance 

        Returns
        -------
        distribution : object
            Distribution class or its instance (when provenance is not None)
        """
        # Handle distributions that don't follow the assumed naming structure.
        special_dists = {"svn": "SVNDistribution"}
        special_modules = {"git": "vcs", "svn": "vcs"}

        dlower = distribution_type.lower()
        class_name = special_dists.get(dlower,
                                       dlower.capitalize() + 'Distribution')
        module = import_module('reproman.distributions.' +
                               special_modules.get(dlower, dlower))
        class_ = getattr(module, class_name)
        return class_ if provenance is None else class_(**provenance)

    @abc.abstractmethod
    def initiate(self, session):
        """
        Perform any initialization commands needed in the environment.

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
    base = attrib()  # ???  to define specifics of the system, possibly a docker base
    distributions = TypedList(Distribution)  # list of distributions
    files = attrib(default=Factory(list))  # list of other files
    # runs?  whenever we get to provisioning executions
    #        those would also be useful for tracing for presence of distributions
    #        e.g. depending on what is in the PATH


    def get_distribution(self, dtype):
        """get_distribution(dtype) -> distribution

        Returns the distribution of the specified type in the given 
        environment.  Returns None if there are no matching distributions.  
        Raises ValueError if there is more than one matching distribution.
        """
        dist = None
        for d in self.distributions:
            if isinstance(d, dtype):
                if dist:
                    raise ValueError('multiple %s found' % str(dtype))
                dist = d
        return dist

_register_with_representer(EnvironmentSpec)


# Note: The following was derived from ReproZip's PkgManager class
# (Revised BSD License)

class DistributionTracer(object, metaclass=abc.ABCMeta):
    """Base class for package trackers.

    ATM :term:`Package` describes all of possible "archives" which deliver
    some piece of software or data -- packages by distributions (Debian, conda,
    pip, ...), VCS repositories or even container images -- something which has
    to be installed to fulfill environment spec
    """

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
        return

    # This one assumes that distribution works with "packages"
    # TODO: we might want to create a more specialized sub-class for that purpose
    # and move those methods below into that subclass
    # TODO: moreover this one assumes only detection by the files and
    #       provides a generic implementation which is based on stages:
    #       1. for each file identifying package fields uniquely describing the
    #          package (method `_get_packagefields_for_files`)
    #       2. grouping fields based on the packagefields
    #       3. creating an actual `Package` using those fields for each group
    #          of files.
    #  In principle could be RFed to be more scalable, where there is a "Package
    #  manager", which provides similar "assign file to a package" functionality
    #  and identifying packages as already known to the manager.
    def identify_packages_from_files(self, files, root_key=None):
        """Identifies "packages" for a given collection of files

        From an iterative collection of files, we identify the packages
        that contain the files and any files that are not related.

        Parameters
        ----------
        files : iterable
            Container (e.g. list or set) of file paths
        root_key : string, optional
            When adding a matched file to the returned package dict, represent
            that path as relative to the value of this package field rather a
            full path.

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
                pkgfields = file_to_package_dict[f]
                if pkgfields is None:
                    unknown_files.add(f)
                else:
                    if root_key:
                        f_pkg = op.relpath(f, pkgfields[root_key])
                    else:
                        f_pkg = f
                    pkgfields_hashable = tuple(x for x in pkgfields.items())
                    if pkgfields_hashable in found_packages:
                        found_packages[pkgfields_hashable].files.append(f_pkg)
                        nb_pkg_files += 1
                    else:
                        pkg = self._create_package(**pkgfields)
                        if pkg:
                            found_packages[pkgfields_hashable] = pkg
                            # we store only non-directories within 'files'
                            if not self._session.isdir(f):
                                pkg.files.append(f_pkg)
                            nb_pkg_files += 1
                        else:
                            unknown_files.add(f)

        lgr.debug(
            "%s: %d packages with %d files, and %d other files",
            self.__class__.__name__,
            len(found_packages),
            nb_pkg_files,
            len(unknown_files))

        return list(found_packages.values()), unknown_files

    @abc.abstractmethod
    def _get_packagefields_for_files(self, files):
        """Given a list of files, should return a dict mapping files to a
        dictionary of fields which would be later passed into _create_package
        to actually create packages while grouping into packages
        (having identical returned packagefield values)
        """
        return

    @abc.abstractmethod
    def _create_package(self, **package_fields):
        """Creates implementation-specific Package object using fields
        provided by _get_packagefields_for_files
        """
        return


class SpecDiff:

    """Difference object for SpecObjects.

    Instantiate with SpecDiff(a, b).  a and b must be of the same type 
    or TypeError is raised.  Either (but not both) may be None.

    Attributes:

        a, b: The two objects being compared.

        If _diff_cmp_fields is defined for the SpecObjects:

            diff_cmp_id: The _diff_cmp_id of the two objects.  If 
                        _diff_cmp_id are different for the two objects, 
                        they cannot be compared and ValueError is raised.

            diff_vals_a, diff_vals_b: _diff_vals for a and b, respectively, 
                                    or None if a or b is None.

        For collection SpecObjects (e.g. DebianDistribution, containing 
        DEBPackages; these have _collection_attribute defined), we also 
        have:

            collection: a list of SpecDiff objects for the contained 
                        SpecObjects.
    """

    def __init__(self, a, b):
        if not isinstance(a, (SpecObject, type(None))) \
            or not isinstance(b, (SpecObject, type(None))):
            raise TypeError('objects must be SpecObjects or None')
        if not a and not b:
            raise TypeError('objects cannot both be None')
        if a and b and type(a) != type(b):
            raise TypeError('objects must be of the same type')
        self.cls = type(a) if a is not None else type(b)
        self.a = a
        self.b = b
        if self.cls._diff_cmp_fields:
            if a and b and a._diff_cmp_id != b._diff_cmp_id:
                raise ValueError('objects\' _diff_cmp_id differ')
            self.diff_vals_a = a._diff_vals if a else None
            self.diff_vals_b = b._diff_vals if b else None
            self.diff_cmp_id = a._diff_cmp_id if a else b._diff_cmp_id
        if hasattr(a, '_collection_attribute'):
            self.collection = []
            a_collection = { c._diff_cmp_id: c for c in a.collection } if a else {}
            b_collection = { c._diff_cmp_id: c for c in b.collection } if b else {}
            all_cmp_ids = set(a_collection).union(b_collection)
            for cmp_id in all_cmp_ids:
                ac = a_collection[cmp_id] if cmp_id in a_collection else None
                bc = b_collection[cmp_id] if cmp_id in b_collection else None
                self.collection.append(SpecDiff(ac, bc))
        return
