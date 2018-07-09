# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ...formats import Provenance

import logging
from mock import MagicMock, patch

from niceman.utils import swallow_logs
from niceman.utils import items_to_dict
from niceman.tests.utils import assert_in


def test_distributions(demo1_spec):

    def mock_execute_command(command):
        if isinstance(command, list):
            if command == ['apt-cache', 'policy', 'libc6-dev:amd64']:
                return (
                    b'libc6-dev: \
                        Installed: (none) \
                        Candidate: 2.19-18+deb8u4 \
                        Version table: \
                            2.19-18+deb8u4 500 \
                            500 http://archive.ubuntu.com/ubuntu xenial/universe amd64 Packages',
                    0
                )
            if command == ['apt-cache', 'policy', 'afni:amd64']:
                return (
                    b'afni: \
                        Installed: 16.2.07~dfsg.1-2~nd90+1 \
                        Candidate: 16.2.07~dfsg.1-2~nd90+1 \
                        Version table: \
                            16.2.07~dfsg.1-2~nd90+1 500 \
                            500 http://archive.ubuntu.com/ubuntu xenial/universe amd64 Packages',
                    0
                )
            if command == ['apt-cache', 'policy', 'dcm2niix:amd64']:
                return (
                    b'dcm2niix: \
                        Installed: (none) \
                        Candidate: 1:1.0.20171017+git3-g9ccc4c0-1~nd16.04+1 \
                        Version table: \
                            1:1.0.20171017+git3-g9ccc4c0-1~nd16.04+1 500 \
                            500 http://archive.ubuntu.com/ubuntu xenial/universe amd64 Packages',
                    0
                )
        if isinstance(command, str):
            if command.startswith('grep'):
                return (None, 1)

    provenance = Provenance.factory(demo1_spec)
    distributions = provenance.get_distributions()
    distributions = items_to_dict(distributions)
    assert set(distributions.keys()) == {'conda', 'debian'}
    # Test DebianDistribution class.
    debian_distribution = distributions['debian']
    environment = MagicMock()
    environment.execute_command = mock_execute_command
    environment.exists.return_value = False

    with patch('requests.get') as requests, \
        swallow_logs(new_level=logging.DEBUG) as log:

        requests.return_value = type("TestObject", (object,), {})()
        requests.return_value.text = '<a href="/archive/debian/20171208T032012Z/dists/sid/">next change</a>'

        debian_distribution.initiate(environment)
        debian_distribution.install_packages(environment)

        assert_in("Adding Debian update to environment command list.", log.lines)
        assert_in("Adding line 'deb http://snapshot.debian.org/archive/debian/20170531T084046Z/ sid main \
contrib non-free' to /etc/apt/sources.list.d/niceman.sources.list", log.lines)
        assert_in("Adding line 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ \
xenial main contrib non-free' to /etc/apt/sources.list.d/niceman.sources.list", log.lines)
        assert_in("Adding line 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ \
xenial main contrib non-free' to /etc/apt/sources.list.d/niceman.sources.list", log.lines)
        assert_in('Installing libc6-dev=2.19-18+deb8u4, afni=16.2.07~dfsg.1-5~nd16.04+1, \
dcm2niix=1:1.0.20171017+git3-g9ccc4c0-1~nd16.04+1', log.lines)

    """
    no longer in that demo spec
    
    # Test PypiDistribution class.
    pypi_distribution = distributions[4]
    environment = MagicMock()

    pypi_distribution.initiate(environment)
    pypi_distribution.install_packages(environment)

    calls = [
        call.add_command(['pip', 'install', 'piponlypkg']),
    ]
    environment.assert_has_calls(calls, any_order=True)
    """