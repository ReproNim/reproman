# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Module to help maintain a registry of versions for external modules etc
"""
import sys
from os import linesep

from distutils.version import LooseVersion

from reproman.dochelpers import exc_str
from reproman.log import lgr
from .exceptions import CommandError

__all__ = ['UnknownVersion', 'ExternalVersions', 'external_versions']


# To depict an unknown version, which can't be compared by mistake etc
class UnknownVersion:
    """For internal use
    """

    def __str__(self):
        return "UNKNOWN"

    def __cmp__(self, other):
        if other is self:
            return 0
        raise TypeError("UNKNOWN version is not comparable")


#
# Custom handlers
#
from reproman.cmd import Runner
from reproman.support.exceptions import (
    MissingExternalDependency,
    OutdatedExternalDependency,
)
_runner = Runner()


def _get_annex_version():
    """Return version of available git-annex"""
    return _runner.run('git annex version --raw'.split())[0]


def _get_git_version():
    """Return version of available git"""
    return _runner.run('git version'.split())[0].split()[-1]


def _get_apt_cache_version():
    """Return version of available apt-cache."""
    return _runner.run('apt-cache -v'.split())[0].split()[1]


def _get_system_ssh_version():
    """Return version of ssh available system-wide
    """
    try:
        out, err = _runner.run('ssh -V'.split(),
                               expect_fail=True, expect_stderr=True)
        # apparently spits out to err but I wouldn't trust it blindly
        if err.startswith('OpenSSH'):
            out = err
        assert out.startswith('OpenSSH')  # that is the only one we care about atm
        return out.split(' ', 1)[0].rstrip(',.').split('_')[1]
    except CommandError as exc:
        lgr.debug("Could not determine version of ssh available: %s", exc_str(exc))
        return None


def _get_singularity_version():
    """Return version of available singularity."""
    # example output:
    #  "singularity version 3.0.3+ds"
    #  "2.6.1-dist"
    out = _runner.run(["singularity", "--version"])[0]
    return out.split(' ')[-1].split("-")[0].split("+")[0]


def _get_svn_version():
    """Return version of available SVN."""
    # Example output:
    #
    # svn, version 1.9.5 (r1770682)
    # [...]
    return _runner.run(["svn", "--version"])[0].split()[2]


def _get_condor_version():
    """Return version of available condor"""
    # Example output:
    #
    # $CondorVersion: 8.6.8 Nov 30 2017 BuildID: [...]
    return _runner.run(['condor_version'])[0].split()[1]


class ExternalVersions(object):
    """Helper to figure out/use versions of the externals (modules, cmdline tools, etc).

    To avoid collision between names of python modules and command line tools,
    prepend names for command line tools with `cmd:`.

    It maintains a dictionary of `distuil.version.LooseVersion`s to make
    comparisons easy. Note that even if version string conform the StrictVersion
    "standard", LooseVersion will be used.  If version can't be deduced for the
    external, `UnknownVersion()` is assigned.  If external is not present (can't
    be imported, or custom check throws exception), None is returned without
    storing it, so later call will re-evaluate fully.
    """

    UNKNOWN = UnknownVersion()

    CUSTOM = {
        'cmd:annex': _get_annex_version,
        'cmd:git': _get_git_version,
        'cmd:singularity': _get_singularity_version,
        'cmd:system-ssh': _get_system_ssh_version,
        'cmd:svn': _get_svn_version,
        'cmd:condor': _get_condor_version,
        'cmd:apt-cache': _get_apt_cache_version
    }
    INTERESTING = (
        'appdirs',
        'humanize',
        'requests',
        'six',
    )

    def __init__(self):
        self._versions = {}

    @classmethod
    def _deduce_version(klass, value):
        version = None

        # see if it is something containing a version
        for attr in ('__version__', 'version'):
            if hasattr(value, attr):
                version = getattr(value, attr)
                break

        # try pkg_resources
        if version is None and hasattr(value, '__name__'):
            try:
                import pkg_resources
                version = pkg_resources.get_distribution(value.__name__).version
            except Exception:
                pass

        # assume that value is the version
        if version is None:
            version = value

        # do type analysis
        if isinstance(version, (tuple, list)):
            #  Generate string representation
            version = ".".join(str(x) for x in version)
        elif isinstance(version, bytes):
            version = version.decode()
        elif isinstance(version, str):
            pass
        else:
            version = None

        if version:
            return LooseVersion(version)
        else:
            return klass.UNKNOWN

    def __getitem__(self, module):
        # when ran straight in its source code -- fails to discover nipy's version.. TODO
        #if module == 'nipy':
        #    import pdb; pdb.set_trace()
        if not isinstance(module, str):
            modname = module.__name__
        else:
            modname = module
            module = None

        # Early returns None so we do not store prev result for  them
        # and allow users to install things at run time, so later check
        # doesn't pick it up from the _versions
        if modname not in self._versions:
            version = None   # by default -- not present
            if modname in self.CUSTOM:
                try:
                    version = self.CUSTOM[modname]()
                    version = self._deduce_version(version)
                except Exception as exc:
                    lgr.debug("Failed to deduce version of %s due to %s"
                              % (modname, exc_str(exc)))
                    return None
            else:
                if module is None:
                    if modname not in sys.modules:
                        try:
                            module = __import__(modname)
                        except ImportError:
                            lgr.debug("Module %s seems to be not present" % modname)
                            return None
                        except Exception as exc:
                            lgr.warning("Failed to import module %s due to %s",
                                        modname, exc_str(exc))
                            return None
                    else:
                        module = sys.modules[modname]
                if module:
                    version = self._deduce_version(module)
            self._versions[modname] = version

        return self._versions.get(modname, self.UNKNOWN)

    def keys(self):
        """Return names of the known modules"""
        return self._versions.keys()

    def __contains__(self, item):
        return bool(self[item])

    @property
    def versions(self):
        """Return dictionary (copy) of versions"""
        return self._versions.copy()

    def dumps(self, indent=None, preamble="Versions:", query=False):
        """Return listing of versions as a string

        Parameters
        ----------
        indent: bool or str, optional
          If set would instruct on how to indent entries (if just True, ' '
          is used). Otherwise returned in a single line
        preamble: str, optional
          What preamble to the listing to use
        query : bool, optional
          To query for versions of all "registered" custom externals, so to
          get those which weren't queried for yet
        """
        if query:
            [self[k] for k in tuple(self.CUSTOM) + self.INTERESTING]
        if indent and (indent is True):
            indent = ' '
        items = ["%s=%s" % (k, self._versions[k]) for k in sorted(self._versions)]
        out = "%s" % preamble if preamble else ''
        if indent is not None:
            if preamble:
                preamble += linesep
            indent = ' ' if indent is True else str(indent)
            out += (linesep + indent).join(items) + linesep
        else:
            out += " " + ' '.join(items)
        return out

    def check(self, name, min_version=None, msg=""):
        """Check if an external (optionally of specified min version) present

        Parameters
        ----------
        name: str
          Name of the external (typically a Python module)
        min_version: str or version, optional
          Minimal version to satisfy
        msg: str, optional
          An additional message to include into the exception message

        Raises
        ------
        MissingExternalDependency
          if the external is completely missing
        OutdatedExternalDependency
          if the external is present but does not satisfy the min_version
        """
        ver_present = self[name]
        if ver_present is None:
            raise MissingExternalDependency(
                name, ver=min_version, msg=msg)
        elif min_version and ver_present < min_version:
            raise OutdatedExternalDependency(
                name, ver=min_version, ver_present=ver_present, msg=msg)


external_versions = ExternalVersions()
