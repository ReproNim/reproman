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
from repronim.tests.test_constants import DEMO_SPEC1


def test_install_debian_packages(tmpdir):
    """
    Test creating distribution objects from a provenance file.
    """

    provenance_file = tmpdir.join("demo_spec1.yml")
    provenance_file.write(DEMO_SPEC1)

    provenance = Provenance.factory(provenance_file.strpath, 'repronimspec')
    container = MagicMock()

    with swallow_logs(new_level=logging.DEBUG) as log:

        for distribution in provenance.get_distributions():
            distribution.initiate(container)
            distribution.install_packages(container)

        calls = [
            call.add_command(['apt-get', 'update']),
            call.add_command(['apt-get', 'install', '-y', 'libc6-dev']),
            call.add_command(['apt-get', 'install', '-y', 'python-nibabel']),
            call.add_command(['apt-get', 'update']),
            call.add_command(['apt-get', 'update']),
            call.add_command(['apt-get', 'install', '-y', 'afni']),
            call.add_command(['apt-get', 'install', '-y', 'python-nibabel']),
            call.add_command(['conda', 'install', 'numpy'])
        ]
        container.assert_has_calls(calls)
        assert_in("Adding Debian update to container command list.", log.lines)
