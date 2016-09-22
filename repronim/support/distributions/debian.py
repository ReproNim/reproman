# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
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
        afni:
          Installed: 16.2.07~dfsg.1-2~nd90+1
          Candidate: 16.2.07~dfsg.1-2~nd90+1
          Version table:
         *** 16.2.07~dfsg.1-2~nd90+1 500
                500 http://neuro.debian.net/debian stretch/contrib amd64 Packages
                100 /var/lib/dpkg/status
        python-nibabel:
          Installed: 2.1.0-1
          Candidate: 2.1.0-1
          Version table:
         *** 2.1.0-1 900
                900 http://http.debian.net/debian stretch/main amd64 Packages
                900 http://http.debian.net/debian stretch/main i386 Packages
                600 http://http.debian.net/debian sid/main amd64 Packages
                600 http://http.debian.net/debian sid/main i386 Packages
                100 /var/lib/dpkg/status
             2.1.0-1~nd90+1 500
                500 http://neuro.debian.net/debian stretch/main amd64 Packages
                500 http://neuro.debian.net/debian stretch/main i386 Packages

    should provide paths to release files

        /var/lib/apt/lists/http.debian.net_debian_dists_stretch_InRelease
        /var/lib/apt/lists/neuro.debian.net_debian_dists_stretch_InRelease

    """