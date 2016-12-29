# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.cmdline.main import main
from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in
import repronim.tests.fixtures

import logging


def test_ls_output(repronim_cfg_path):
    """
    Test listing the resources.
    """

    args = ['ls',
            '--config', repronim_cfg_path,
    ]

    with swallow_logs(new_level=logging.DEBUG) as log:
        main(args)

        assert_in("listing resource my-debian", log.lines)
        assert_in("listing resource my-aws-subscription", log.lines)
        assert_in("listing resource ec2-workflow", log.lines)
        assert_in("listing resource remote-docker", log.lines)