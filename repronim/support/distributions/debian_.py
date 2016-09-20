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
    return DebianReleaseSpec(*[
            release.get(a.name.title(), None)
            for a in attr.fields(DebianReleaseSpec)]
    )