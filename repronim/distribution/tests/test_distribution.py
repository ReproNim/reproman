# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.provenance import Provenance

import logging
from mock import MagicMock, call

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in

import repronim.tests.fixtures

def test_install_debian_packages(demo1_spec):
    """
    Test creating distribution objects from a provenance file.
    """

    provenance = Provenance.factory(demo1_spec, 'repronimspec')
    container = MagicMock()

    with swallow_logs(new_level=logging.DEBUG) as log:

        for distribution in provenance.get_distributions():
            distribution.initiate(container)
            distribution.install_packages(container)

        calls = [
            call.add_command(['apt-get', 'update']),
            call.add_command(['apt-get', 'install', '-y', 'python-pip']),
            call.add_command(['apt-get', 'install', '-y', 'libc6-dev']),
            call.add_command(['apt-get', 'install', '-y', 'python-nibabel']),
            call.add_command(['apt-get', 'install', '-y', 'afni']),
            call.add_command(['pip', 'install', 'piponlypkg'])
        ]
        container.assert_has_calls(calls, any_order=True)
        assert_in("Adding Debian update to environment command list.", log.lines)
