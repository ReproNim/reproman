# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
import mock
from six.moves import StringIO

from niceman.api import backend_parameters
from niceman.utils import swallow_logs


def test_backend_parameters_unknown_resource():
    with swallow_logs(new_level=logging.WARNING) as log:
        backend_parameters(["i'm-unknown"])
        assert "Failed to import" in log.out


def test_backend_parameters_with_arg():
    with mock.patch('sys.stdout', new_callable=StringIO) as out:
        backend_parameters(["ssh"])
    assert "host:" in out.getvalue()
    assert "aws_ec2" not in out.getvalue()


def test_backend_parameters_all():
    with mock.patch('sys.stdout', new_callable=StringIO) as out:
        backend_parameters()
    assert "host:" in out.getvalue()
    assert "aws_ec2" in out.getvalue()
