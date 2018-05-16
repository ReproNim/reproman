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
from ..debian import parse_dpkgquery_line

from niceman.tests.utils import eq_, assert_is_subset_recur


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


def test_parse_apt_cache_show_pkgs_output():
    from ..debian import parse_apt_cache_show_pkgs_output
    txt1 = """\
Package: openssl
Status: install ok installed
Priority: optional
Section: utils
Installed-Size: 934
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Architecture: amd64
Version: 1.0.2g-1ubuntu4.5
Depends: libc6 (>= 2.15), libssl1.0.0 (>= 1.0.2g)
Suggests: ca-certificates
Conffiles:
 /etc/ssl/openssl.cnf 7df26c55291b33344dc15e3935dabaf3
Description-en: Secure Sockets Layer toolkit - cryptographic utility
 This package is part of the OpenSSL project's implementation of the SSL
 and TLS cryptographic protocols for secure communication over the
 Internet.
 .
 It contains the general-purpose command line binary /usr/bin/openssl,
 useful for cryptographic operations such as:
  * creating RSA, DH, and DSA key parameters;
  * creating X.509 certificates, CSRs, and CRLs;
  * calculating message digests;
  * encrypting and decrypting with ciphers;
  * testing SSL/TLS clients and servers;
  * handling S/MIME signed or encrypted mail.
Description-md5: 9b6de2bb6e1d9016aeb0f00bcf6617bd
Original-Maintainer: Debian OpenSSL Team <pkg-openssl-devel@lists.alioth.debian.org>

Package: openssl
Priority: standard
Section: utils
Installed-Size: 934
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Original-Maintainer: Debian OpenSSL Team <pkg-openssl-devel@lists.alioth.debian.org>
Architecture: amd64
Source: openssl-src (1.0.2g)
Version: 1.0.2g-1ubuntu4
Depends: libc6 (>= 2.15), libssl1.0.0 (>= 1.0.2g)
Suggests: ca-certificates
Filename: pool/main/o/openssl/openssl_1.0.2g-1ubuntu4_amd64.deb
Size: 492190
MD5sum: 8280148dc2991da94be5810ad4d91552
SHA1: b5326f27aae83c303ff934121dede47d9fce7c76
SHA256: e897ffc8d84b0d436baca5dbd684a85146ffa78d3f2d15093779d3f5a8189690
Description-en: Secure Sockets Layer toolkit - cryptographic utility
 This package is part of the OpenSSL project's implementation of the SSL
 and TLS cryptographic protocols for secure communication over the
 Internet.
 .
 It contains the general-purpose command line binary /usr/bin/openssl,
 useful for cryptographic operations such as:
  * creating RSA, DH, and DSA key parameters;
  * creating X.509 certificates, CSRs, and CRLs;
  * calculating message digests;
  * encrypting and decrypting with ciphers;
  * testing SSL/TLS clients and servers;
  * handling S/MIME signed or encrypted mail.
Description-md5: 9b6de2bb6e1d9016aeb0f00bcf6617bd
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
Origin: Ubuntu
Supported: 5y
Task: standard, ubuntu-core, ubuntu-core, mythbuntu-frontend, mythbuntu-backend-slave, mythbuntu-backend-master, ubuntu-touch-core, ubuntu-touch, ubuntu-sdk-libs-tools, ubuntu-sdk

Package: alienblaster
Priority: extra
Section: universe/games
Installed-Size: 668
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Original-Maintainer: Debian Games Team <pkg-games-devel@lists.alioth.debian.org>
Architecture: amd64
Source: alienblaster-src
Version: 1.1.0-9
Depends: alienblaster-data, libc6 (>= 2.14), libgcc1 (>= 1:3.0), libsdl-mixer1.2, libsdl1.2debian (>= 1.2.11), libstdc++6 (>= 5.2)
Filename: pool/universe/a/alienblaster/alienblaster_1.1.0-9_amd64.deb
Size: 180278
MD5sum: e53379fd0d60e0af6304af78aa8ef2b7
SHA1: ca405056cf66a1c2ae3ae1674c22b7d24cda4986
SHA256: ff25bd843420801e9adea4f5ec1ca9656b2aeb327d8102107bf5ebbdb3046c38
Description-en: Classic 2D shoot 'em up
 Your mission is simple: Stop the invasion of the aliens and blast them!
 .
 Alien Blaster is a classic 2D shoot 'em up featuring lots of different
 weapons, special items, aliens to blast and a big bad boss.
 .
 It supports both a single player mode and a cooperative two player mode
 for two persons playing on one computer.
Description-md5: da1f8f1a6453d62874036331e075d65f
Homepage: http://www.schwardtnet.de/alienblaster/
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
Origin: Ubuntu
"""
    out1 = [{'architecture': 'amd64',
             'package': 'openssl',
             'status': 'install ok installed',
             'version': '1.0.2g-1ubuntu4.5'},
            {'architecture': 'amd64',
             'source_name': 'openssl-src',
             'source_version': '1.0.2g',
             'package': 'openssl',
             'version': '1.0.2g-1ubuntu4'},
            {'architecture': 'amd64',
             'source_name': 'alienblaster-src',
             'package': 'alienblaster',
             'md5': 'e53379fd0d60e0af6304af78aa8ef2b7',
             'version': '1.1.0-9'},
            ]
    out = parse_apt_cache_show_pkgs_output(txt1)
    assert_is_subset_recur(out1, out, [dict, list])


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
openssl:
  Installed: 1.0.2g-1ubuntu4.5
  Candidate: 1.0.2g-1ubuntu4.8
  Version table:
     1.0.2g-1ubuntu4.8 500
        500 http://us.archive.ubuntu.com/ubuntu xenial-updates/main amd64 Packages
     1.0.2g-1ubuntu4.6 500
        500 http://security.ubuntu.com/ubuntu xenial-security/main amd64 Packages
 *** 1.0.2g-1ubuntu4.5 100
        100 /var/lib/dpkg/status
     1.0.2g-1ubuntu4 500
        500 http://us.archive.ubuntu.com/ubuntu xenial/main amd64 Packages
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
alienblaster:
  Installed: 1.1.0-9
  Candidate: 1.1.0-9
  Version table:
 *** 1.1.0-9 500
        500 http://us.archive.ubuntu.com/ubuntu xenial/universe amd64 Packages
        500 file:/my/repo ./ Packages
        500 file:/my/repo2 ubuntu/ Packages
        100 /var/lib/dpkg/status
skype:i386:
  Installed: (none)
  Candidate: (none)
  Version table:
     4.3.0.37-1 -1
        100 /var/lib/dpkg/status
"""
    out1 = {'openssl': {'architecture': None,
             'candidate': '1.0.2g-1ubuntu4.8',
             'installed': '1.0.2g-1ubuntu4.5',
             'versions': [{'installed': None,
                           'priority': '500',
                           'sources': [{'priority': '500',
                                        'source': 'http://us.archive.ubuntu.com/ubuntu '
                                                  'xenial-updates/main amd64 '
                                                  'Packages'}],
                           'version': '1.0.2g-1ubuntu4.8'},
                          {'installed': None,
                           'priority': '500',
                           'sources': [{'priority': '500',
                                        'source': 'http://security.ubuntu.com/ubuntu '
                                                  'xenial-security/main amd64 '
                                                  'Packages'}],
                           'version': '1.0.2g-1ubuntu4.6'},
                          {'installed': '***',
                           'priority': '100',
                           'sources': [{'priority': '100',
                                        'source': '/var/lib/dpkg/status'}],
                           'version': '1.0.2g-1ubuntu4.5'},
                          {'installed': None,
                           'priority': '500',
                           'sources': [{'priority': '500',
                                        'source': 'http://us.archive.ubuntu.com/ubuntu '
                                                  'xenial/main amd64 '
                                                  'Packages'}],
                           'version': '1.0.2g-1ubuntu4'}]}}
    out = parse_apt_cache_policy_pkgs_output(txt1)
    assert_is_subset_recur(out1, out, [dict])

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
 500 http://debproxy:9999/debian/ jessie-backports/contrib Translation-en
 100 http://debproxy:9999/debian/ jessie-backports/non-free amd64 Packages
     release o=Debian Backports,a=jessie-backports,n=jessie-backports,l=Debian Backports,c=non-free
     origin debproxy
 500 http://us.archive.ubuntu.com/ubuntu xenial-updates/universe amd64 Packages
     release v=16.04,o=Ubuntu,a=xenial-updates,n=xenial,l=Ubuntu,c=universe,b=amd64
     origin us.archive.ubuntu.com
 500 http://us.archive.ubuntu.com/ubuntu xenial-updates/multiverse i386 Packages
     release v=16.04,o=Ubuntu,a=xenial-updates,n=xenial,l=Ubuntu,c=multiverse,b=i386
     origin us.archive.ubuntu.com
Pinned packages:
"""
    out1 = {'http://neuro.debian.net/debian xenial/non-free i386 Packages':
                {'architecture': 'i386',
                 'archive': 'xenial',
                 'archive_uri': 'http://neuro.debian.net/debian',
                 'uri_suite': 'xenial',
                 'codename': 'xenial',
                 'component': 'non-free',
                 'label': 'NeuroDebian',
                 'origin': 'NeuroDebian',
                 'site': 'neuro.debian.net'
                 },
            'http://security.ubuntu.com/ubuntu xenial-security/restricted amd64 Packages':
                {'architecture': 'amd64',
                 'archive': 'xenial-security',
                 'archive_uri': 'http://security.ubuntu.com/ubuntu',
                 'uri_suite': 'xenial-security',
                 'codename': 'xenial',
                 'component': 'restricted',
                 'label': 'Ubuntu',
                 'origin': 'Ubuntu',
                 'site': 'security.ubuntu.com'
                 },
            'http://debproxy:9999/debian/ jessie-backports/contrib Translation-en':
                {'archive_uri': 'http://debproxy:9999/debian/',
                 'uri_suite': 'jessie-backports'
                 },
            'http://debproxy:9999/debian/ jessie-backports/non-free amd64 Packages':
                {'archive': 'jessie-backports',
                 'archive_uri': 'http://debproxy:9999/debian/',
                 'codename': 'jessie-backports',
                 'component': 'non-free',
                 'label': 'Debian Backports',
                 'origin': 'Debian Backports',
                 'site': 'debproxy',
                 'uri_suite': 'jessie-backports'
                 },
            }
    out = parse_apt_cache_policy_source_info(txt)
    assert_is_subset_recur(out1, out, [dict])


def test_get_apt_release_file_names():
    from ..debian import get_apt_release_file_names
    fn = get_apt_release_file_names('http://us.archive.ubuntu.com/ubuntu',
                                    'xenial-backports')
    assert "/var/lib/apt/lists/us.archive.ubuntu.com_ubuntu_dists_xenial-backports_InRelease" in fn
    assert "/var/lib/apt/lists/us.archive.ubuntu.com_ubuntu_dists_xenial-backports_Release" in fn
    fn = get_apt_release_file_names('file:/my/repo2/ubuntu',None)
    assert "/var/lib/apt/lists/_my_repo2_ubuntu_InRelease" in fn
    assert "/var/lib/apt/lists/_my_repo2_ubuntu_Release" in fn


def test_parse_dpkgquery_line():
    for line, expected in [
            ('zlib1g:i386: /lib/i386-linux-gnu/libz.so.1.2.8',
             {'name': 'zlib1g',
              'architecture': 'i386',
              'path': '/lib/i386-linux-gnu/libz.so.1.2.8',
              'pkgs_rest': None}),
            ('fail2ban: /usr/bin/fail2ban-client',
             {'name': 'fail2ban',
              'path': '/usr/bin/fail2ban-client',
              'pkgs_rest': None}),
            ('fsl-5.0-eddy-nonfree, fsl-5.0-core: /usr/lib/fsl/5.0',
             {'name': 'fsl-5.0-eddy-nonfree',
              'path': '/usr/lib/fsl/5.0',
              'pkgs_rest': ', fsl-5.0-core'}),
            ('pkg: path,with,commas',
             {'name': 'pkg',
              'path': 'path,with,commas',
              'pkgs_rest': None}),
            ('diversion by dash from: /bin/sh', None)
    ]:
        assert parse_dpkgquery_line(line) == expected
