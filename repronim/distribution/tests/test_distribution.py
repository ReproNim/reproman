# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ...provenance import Provenance

import logging
from mock import MagicMock, call

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in

import repronim.tests.fixtures

def test_distributions(demo1_spec):

    provenance = Provenance.factory(demo1_spec)
    distributions = provenance.get_distributions()

    # Test DebianDistribution class.
    debian_distribution = distributions[0]
    environment = MagicMock()

    with swallow_logs(new_level=logging.DEBUG) as log:

        debian_distribution.initiate(environment)
        debian_distribution.install_packages(environment)

        calls = [
            call.add_command(['apt-get', 'update']),
            call.add_command(['apt-get', 'install', '-y', 'python-pip']),
            call.add_command(['apt-get', 'install', '-y', 'libc6-dev']),
            call.add_command(['apt-get', 'install', '-y', 'python-nibabel']),
        ]
        environment.assert_has_calls(calls, any_order=True)
        assert_in("Adding Debian update to environment command list.", log.lines)


    # Test PypiDistribution class.
    pypi_distribution = distributions[4]
    environment = MagicMock()

    pypi_distribution.initiate(environment)
    pypi_distribution.install_packages(environment)

    calls = [
        call.add_command(['pip', 'install', 'piponlypkg']),
    ]
    environment.assert_has_calls(calls, any_order=True)
