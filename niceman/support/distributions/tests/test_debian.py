# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Various supporting utilities for various distributions

"""

try:
    from ..debian import DebianReleaseSpec
    from ..debian import get_spec_from_release_file
except:
    DebianReleaseSpec = None

from niceman.tests.utils import with_tempfile
from niceman.tests.utils import eq_
from niceman.tests.utils import skip_if


@skip_if(not DebianReleaseSpec)
@with_tempfile(content="""\
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA256

Origin: NeuroDebian
Label: NeuroDebian2
Suite: stretch
Codename: stretch2
Date: Thu, 15 Sep 2016 01:30:57 UTC
Architectures: i386 amd64 sparc
Components: main non-free contrib
Description: NeuroDebian repository with perspective, inofficial and backported packages -- mostly neuroscience-related
MD5Sum:
 d9650396c56a6f9521d0bbd9f719efbe 482669 main/binary-i386/Packages
 34134c9a64b847d33eeeb3cc7291f855ab9f0969e8ad7c92cd2a0c1aebc19d1e 14199 contrib/Contents-sparc.gz
-----BEGIN PGP SIGNATURE-----
Version: GnuPG v2

iEYEAREIAAYFAlfZ+dEACgkQpdMvASZJpamBowCfXOPQimiIy2wnVY5U9sLs1jSn
JZ0An0Uoocusvjco1t6RAwxt/y3lQoWV
=a3Nn
-----END PGP SIGNATURE-----
""")
def test_get_spec_from_release_file(f=None):
    # ATM -- plain one to one, no conversions
    eq_(get_spec_from_release_file(f),
        DebianReleaseSpec(
            origin='NeuroDebian',
            label='NeuroDebian2',
            codename='stretch2',
            version=None,
            suite='stretch',
            date='Thu, 15 Sep 2016 01:30:57 UTC',
            components='main non-free contrib',
            architectures='i386 amd64 sparc',
        ))


def test_parse_apt_cache_policy_pkgs_output():
    from ..debian import parse_apt_cache_policy_pkgs_output
    txt1 = """\
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
python-biotools:
  Installed: (none)
  Candidate: 1.2.12-2
  Version table:
     1.2.12-2 600
        600 http://http.debian.net/debian sid/main amd64 Packages
        600 http://http.debian.net/debian sid/main i386 Packages
skype:i386:
  Installed: (none)
  Candidate: (none)
  Version table:
     4.3.0.37-1 -1
        100 /var/lib/dpkg/status
"""
    out1 = {'afni': None, 'python-nibabel': None}
    out = parse_apt_cache_policy_pkgs_output(txt1)
    from pprint import pprint
    print(len(out))
    pprint(out)
