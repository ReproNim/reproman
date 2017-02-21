# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from mock import patch

from ...cmdline.main import main
from ...utils import swallow_logs
from ...tests.utils import assert_in

import logging


def test_ls_output(niceman_cfg_path):
    """
    Test listing the resources.
    """

    args = ['ls',
            '--config', niceman_cfg_path,
    ]

    with patch('docker.Client'), \
            patch('boto3.resource'), \
         swallow_logs(new_level=logging.DEBUG) as log:

        main(args)

        assert_in('Retrieved resource remote-docker', log.lines)
        assert_in("Retrieved resource my-aws-subscription", log.lines)
        assert_in("Retrieved resource ec2-workflow", log.lines)
        assert_in("Retrieved resource remote-docker", log.lines)