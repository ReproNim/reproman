# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.distribution import Distribution
from repronim.provenance import Provenance

import logging

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in
from repronim.tests.test_constants import REPROZIP_OUTPUT


def test_get_debian_packages(tmpdir):
    """
    Test retrieving commands for 2 Debian packages from provenance.
    """

    provenance_file = tmpdir.join("reprozip.yml")
    provenance_file.write(REPROZIP_OUTPUT)

    provenance = Provenance.factory(provenance_file.strpath, 'reprozip')
    distribution = Distribution.factory('debian', provenance)

    with swallow_logs(new_level=logging.DEBUG) as log:

        commands = []
        for command in distribution.get_install_package_commands():
            commands.append(command)
        assert commands == [
            ['apt-get', 'update'],
            ['apt-get', 'install', '-y', 'base-files'],
            ['apt-get', 'install', '-y', 'bc']
        ]

        assert_in("Generating command for package: base-files", log.lines)
        assert_in("Generating command for package: bc", log.lines)
