# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Various supporting utilities for Debian(-based) distributions

"""

from __future__ import absolute_import

# Let's try to use attr module
import attr

import codecs
from debian import deb822

__docformat__ = 'restructuredtext'


@attr.s
class DebianReleaseSpec(object):
    """Encapsulates knowledge about used Debian release

    origin: Debian
    label: Debian
    suite: stable
    version: 8.5
    codename: jessie
    date: Sat, 04 Jun 2016 13:24:54 UTC
    components: main contrib non-free
    architectures: amd64
    """

    # Those could be different in overlays or other derived distributions
    origin = attr.ib()   # Debian
    label = attr.ib()    # Debian
    codename = attr.ib()
    suite = attr.ib()
    version = attr.ib()
    date = attr.ib()     # in XXX format?
    components = attr.ib()#validator=attr.validators.instance_of(list),convert=str.split),
    architectures = attr.ib()#validator=attr.validators.instance_of(list),convert=str.split)


def get_spec_from_release_file(release_filename):
    """Provide specification object describing the component of the distribution

    Examples
    --------

     SKIP TST FOR NOW >>> get_spec_from_release_file('/var/lib/apt/lists/neuro.debian.net_debian_dists_jessie_InRelease')

    """
    release = deb822.Release(codecs.open(release_filename, 'r', 'utf-8'))
    # TODO: redo with conversions of components and architectures in into lists
    # and date in machine-readable presentation
    return DebianReleaseSpec(**{
            a.name: release.get(a.name.title(), None)
            for a in attr.fields(DebianReleaseSpec)
    })


def get_used_release_specs(package, installed_version=None):
    """Given a name for an installed package, return a set of specs describing
    the release this file could be obtained from

    e.g. for

        $> apt-cache policy afni python-nibabel

    should provide paths to release files

        /var/lib/apt/lists/http.debian.net_debian_dists_stretch_InRelease
        /var/lib/apt/lists/neuro.debian.net_debian_dists_stretch_InRelease

    """
    pass


def _parse_apt_cache_policy_pkgs_output(output):
    # first split per each package
    import re
    entries = filter(bool, re.split('\n(?=\S)', output, flags=re.MULTILINE))
    return entries


def parse_apt_cache_policy_pkgs_output(output):
    import re
    # findall wasn't greedy enough for some reason, so decided first to
    # split into entries (one per package)
    entries = filter(bool, re.split('\n(?=\S)', output, flags=re.MULTILINE))
    # now we need to parse/match each entry
    re_pkg = re.compile("""
        ^(?P<name>[^\s:]+):(?P<architecture>\S+)?\s*\n                       # name of the package
        \s+Installed:\s*(?P<installed>\S*)\s*\n    # Installed version
        \s+Candidate:\s*(?P<candidate>\S*)\s*\n    # Candidate version
        \s+Version\stable:\s*
        (?P<version_table>(\n\s.*)+)
        """, flags=re.VERBOSE)

    re_versions = re.compile("""
        ^(\s{5}|\s(?P<installed>\*\*\*)\s)
        (?P<version>\S+)\s+
        (?P<priority>\S+)\n.*
        (?P<urls>(\n\s{8}.*)+)
    """, flags=re.VERBOSE)
    pkgs = {}
    for entry in entries:
        match = re_pkg.match(entry.strip())
        if not match:
            print("FAILED in ", entry)
            continue
        info = match.groupdict()
        pkgs[info.pop('name')] = info
        info['versions'] = [
            x.groupdict()
            for x in re_versions.finditer(info.pop('version_table'))
        ]
        # process version_table
    return pkgs
    #for pkg_match in re_pkg.finditer(output):
    #    print type(pkg_match), pkg_match.groupdict()