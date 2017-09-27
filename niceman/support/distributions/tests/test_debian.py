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

from ..debian import DebianReleaseSpec
from ..debian import get_spec_from_release_file

from niceman.tests.utils import eq_


def test_get_spec_from_release_file(f=None):
    content = """\
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
"""
    eq_(get_spec_from_release_file(content),
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
# TODO: Test discovered entities
#    from pprint import pprint
#    print(len(out))
#    pprint(out)

def test_parse_apt_cache_policy_source_info():
    from ..debian import parse_apt_cache_policy_source_info
    txt = """\
Package files:
 100 /var/lib/dpkg/status
     release a=now
 500 http://neuro.debian.net/debian xenial/non-free i386 Packages
     release o=NeuroDebian,a=xenial,n=xenial,l=NeuroDebian,c=non-free,b=i386
     origin neuro.debian.net
 500 http://neuro.debian.net/debian xenial/non-free amd64 Packages
     release o=NeuroDebian,a=xenial,n=xenial,l=NeuroDebian,c=non-free,b=amd64
     origin neuro.debian.net
 500 http://neuro.debian.net/debian data/non-free i386 Packages
     release o=NeuroDebian,a=data,n=data,l=NeuroDebian,c=non-free,b=i386
     origin neuro.debian.net
 500 http://neuro.debian.net/debian data/non-free amd64 Packages
     release o=NeuroDebian,a=data,n=data,l=NeuroDebian,c=non-free,b=amd64
     origin neuro.debian.net
 500 file:/my/repo2 ubuntu/ Packages
     release c=
 500 file:/my/repo ./ Packages
     release c=
 500 http://dl.google.com/linux/chrome/deb stable/main amd64 Packages
     release v=1.0,o=Google, Inc.,a=stable,n=stable,l=Google,c=main,b=amd64
     origin dl.google.com
 500 http://security.ubuntu.com/ubuntu xenial-security/restricted i386 Packages
     release v=16.04,o=Ubuntu,a=xenial-security,n=xenial,l=Ubuntu,c=restricted,b=i386
     origin security.ubuntu.com
 500 http://security.ubuntu.com/ubuntu xenial-security/restricted amd64 Packages
     release v=16.04,o=Ubuntu,a=xenial-security,n=xenial,l=Ubuntu,c=restricted,b=amd64
     origin security.ubuntu.com
 500 http://us.archive.ubuntu.com/ubuntu xenial-updates/universe amd64 Packages
     release v=16.04,o=Ubuntu,a=xenial-updates,n=xenial,l=Ubuntu,c=universe,b=amd64
     origin us.archive.ubuntu.com
 500 http://us.archive.ubuntu.com/ubuntu xenial-updates/multiverse i386 Packages
     release v=16.04,o=Ubuntu,a=xenial-updates,n=xenial,l=Ubuntu,c=multiverse,b=i386
     origin us.archive.ubuntu.com
Pinned packages:
"""
    out = parse_apt_cache_policy_source_info(txt)
    # TODO: Test discovered entities
    from pprint import pprint
    print(len(out))
    pprint(out)
