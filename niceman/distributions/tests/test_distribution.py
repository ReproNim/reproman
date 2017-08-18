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
from mock import MagicMock, call

from niceman.utils import swallow_logs
from niceman.utils import items_to_dict
from niceman.tests.utils import assert_in

import niceman.tests.fixtures


def test_distributions(demo1_spec):

    provenance = Provenance.factory(demo1_spec)
    distributions = provenance.get_distributions()
    distributions = items_to_dict(distributions)
    assert set(distributions.keys()) == {'conda', 'debian'}
    # Test DebianDistribution class.
    debian_distribution = distributions['debian']
    environment = MagicMock()

    with swallow_logs(new_level=logging.DEBUG) as log:

        debian_distribution.initiate(environment)
        debian_distribution.install_packages(environment)

        calls = [
            call.execute_command(['apt-get', 'update']),
            call.execute_command(['apt-get', 'install', '-y', 'libc6-dev=2.19-18+deb8u4', 'afni=16.2.07~dfsg.1-2~nd90+1']),
        ]
        environment.assert_has_calls(calls, any_order=True)
        assert_in("Adding Debian update to environment command list.", log.lines)

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