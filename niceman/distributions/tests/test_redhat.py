# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import logging
import pytest
import tempfile
import uuid

from ...cmd import Runner
from ...distributions.redhat import RPMTracer
from ...distributions.redhat import RPMPackage
from ...distributions.redhat import RedhatDistribution
from ...formats import Provenance
from ...resource.docker_container import DockerContainer
from ...tests.utils import skip_if_no_network, skip_if_no_docker_engine
from ...utils import swallow_logs


@skip_if_no_docker_engine
@pytest.fixture(scope='function')
def docker_container():
    skip_if_no_network()
    name = str(uuid.uuid4())  # Generate a random name for the container.
    Runner().run(['docker', 'run', '-t', '-d', '--rm', '--name',
        name, 'centos:7'])
    yield name
    Runner().run(['docker', 'stop', name])


@pytest.fixture(scope='module')
def centos_spec():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    with open(tmp.name, 'w') as f:
        f.write("""# NICEMAN Environment Configuration File
# This file was created by NICEMAN 0.0.5 on 2018-05-23 22:03:22.820177
version: 0.0.1
distributions:
- name: redhat
  sources:
  - id: base/7/x86_64
    name: CentOS-7 - Base
    revision: '1525378614'
    updated: Thu May  3 20:17:37 2018
    mirrors: http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=os&infra=container
    baseurl: http://mirror.wdc1.us.leaseweb.net/centos/7.5.1804/os/x86_64/ (9
    expire: '21600 second(s) (last: Wed May 23 22:02:41 2018)'
    filename: /etc/yum.repos.d/CentOS-Base.repo
  - id: epel/x86_64
    name: Extra Packages for Enterprise Linux 7 - x86_64
    revision: '1527088265'
    updated: Wed May 23 15:25:37 2018
    metalink: https://mirrors.fedoraproject.org/metalink?repo=epel-7&arch=x86_64
    baseurl: http://mirror.math.princeton.edu/pub/epel/7/x86_64/ (35 more)
    expire: '21600 second(s) (last: Wed May 23 22:02:43 2018)'
    filename: /etc/yum.repos.d/epel.repo
  - id: extras/7/x86_64
    name: CentOS-7 - Extras
    revision: '1526808850'
    updated: Sun May 20 09:36:03 2018
    mirrors: http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=extras&infra=container
    baseurl: http://www.gtlib.gatech.edu/pub/centos/7.5.1804/extras/x86_64/ (9
    expire: '21600 second(s) (last: Wed May 23 22:02:43 2018)'
    filename: /etc/yum.repos.d/CentOS-Base.repo
  - id: updates/7/x86_64
    name: CentOS-7 - Updates
    revision: '1527083651'
    updated: Wed May 23 13:58:10 2018
    mirrors: http://mirrorlist.centos.org/?release=7&arch=x86_64&repo=updates&infra=container
    baseurl: http://mirror.math.princeton.edu/pub/centos/7.5.1804/updates/x86_64/
    expire: '21600 second(s) (last: Wed May 23 22:02:43 2018)'
    filename: /etc/yum.repos.d/CentOS-Base.repo
  packages:
  - name: fido
    pkgid: fido-1.1.2-1.el7.x86_64
    version: 1.1.2
    release: 1.el7
    architecture: x86_64
    install_date: Wed May 23 22:03:00 2018
    group: System Environment/Daemons
    size: '116736'
    license: GPLv2+ and LGPLv2+
    signature: RSA/SHA256, Wed Sep 24 16:10:18 2014, Key ID 6a2faea2352c64e5
    source_rpm: fido-1.1.2-1.el7.src.rpm
    build_date: Tue Sep 23 20:23:46 2014
    build_host: buildvm-17.phx2.fedoraproject.org
    packager: Fedora Project
    vendor: Fedora Project
    url: http://www.joedog.org/fido-home/
    files:
    - /usr/sbin/fido
  version: CentOS Linux release 7.4.1708 (Core)
""")
    return tmp.name


@pytest.fixture
def setup_packages():
    """set up the package comparison tests"""
    a = RPMPackage(name='p1')
    b = RPMPackage(name='p1', version='1.0')
    c = RPMPackage(name='p1', version='1.1')
    d = RPMPackage(name='p1', architecture='i386')
    e = RPMPackage(name='p1', architecture='alpha')
    f = RPMPackage(name='p1', version='1.1', architecture='i386')
    g = RPMPackage(name='p2')
    return (a, b, c, d, e, f, g)


@pytest.fixture
def setup_distributions(setup_packages):
    (p1, p1v10, p1v11, p1ai, p1aa, p1v11ai, p2) = setup_packages
    d1 = RedhatDistribution(name='debian 1')
    d1.packages = [p1]
    d2 = RedhatDistribution(name='debian 2')
    d2.packages = [p1v11]
    return (d1, d2)


def test_package_satisfies(setup_packages):
    (p1, p1v10, p1v11, p1ai, p1aa, p1v11ai, p2) = setup_packages
    assert p1.satisfies(p1)
    assert p1v10.satisfies(p1v10)
    assert not p1.satisfies(p1v10)
    assert p1v10.satisfies(p1)
    assert not p1v10.satisfies(p1v11)
    assert not p1.satisfies(p2)
    assert not p1v10.satisfies(p2)
    assert not p2.satisfies(p1v10)
    assert not p1v10.satisfies(p1aa)
    assert p1aa.satisfies(p1)
    assert not p1aa.satisfies(p1v10)
    assert not p1aa.satisfies(p1ai)
    assert not p1v11.satisfies(p1v11ai)
    assert p1v11ai.satisfies(p1v11)


def test_distribution_satisfies_package(setup_distributions, setup_packages):
    (d1, d2) = setup_distributions
    (p1, p1v10, p1v11, p1ai, p1aa, p1v11ai, p2) = setup_packages
    assert d1.satisfies_package(p1)
    assert not d1.satisfies_package(p1v10)
    assert d2.satisfies_package(p1)
    assert not d2.satisfies_package(p1v10)
    assert d2.satisfies_package(p1v11)


def test_distribution_statisfies(setup_distributions):
    (d1, d2) = setup_distributions
    assert not d1.satisfies(d2)
    assert d2.satisfies(d1)


def test_distribution_sub(setup_packages):
    (p1, p1v10, p1v11, p1ai, p1aa, p1v11ai, p2) = setup_packages
    d1 = RedhatDistribution(name='debian 1')
    d1.packages = [p1, p2]
    d2 = RedhatDistribution(name='debian 2')
    d2.packages = [p1v11, p2]
    assert d1-d2 == []
    result = d2-d1
    assert len(result) == 1
    assert result[0] == p1v11


@skip_if_no_docker_engine
def test_tracer(docker_container):
    skip_if_no_network()

    # Test setup
    resource = DockerContainer(docker_container)
    resource.connect()
    session = resource.get_session()
    tracer = RPMTracer(session)
    tracer._init()

    # Test sorting through a given set of files and identifying the ones
    # that belong to CentOS.
    files = ['/usr/bin/ls', 'foo']
    dist, remaining_files = next(tracer.identify_distributions(files))
    assert 'foo' in remaining_files
    assert dist.name == 'redhat'
    assert dist.version.startswith('CentOS Linux release 7')
    source_ids = [s.id for s in dist.sources]
    assert 'base/7/x86_64' in source_ids
    assert 'extras/7/x86_64' in source_ids
    assert 'updates/7/x86_64' in source_ids
    assert dist.packages[0].name == 'coreutils'
    assert dist.packages[0].group == 'System Environment/Base'
    assert dist.packages[0].files[0] == '/usr/bin/ls'

    # Test creating RPMPackage objects with files found to be in CentOS.
    packages = tracer._get_packagefields_for_files(['/usr/bin/ls'])
    assert packages['/usr/bin/ls']['name'] == 'coreutils'
    assert packages['/usr/bin/ls']['packager'].startswith('CentOS BuildSystem')


@skip_if_no_docker_engine
def test_distribution(docker_container, centos_spec):
    skip_if_no_network()

    # Test setup
    resource = DockerContainer(docker_container)
    resource.connect()
    session = resource.get_session()
    provenance = Provenance.factory(centos_spec, 'niceman')
    dist = provenance.get_distributions()[0]

    with swallow_logs(new_level=logging.DEBUG) as log:
        dist.initiate(session)
        assert "Running command ['yum', 'repolist']" in log.lines
        assert "Running command ['yum', 'install', '-y', 'epel-release']" in \
            log.lines

        dist.install_packages(session)
        assert "Installing fido-1.1.2-1.el7.x86_64" in log.lines
        assert "Running command ['yum', 'install', '-y', 'fido-1.1.2-1.el7.x86_64']" \
            in log.lines
