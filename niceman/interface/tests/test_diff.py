# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import join as opj, dirname
from niceman.cmdline.main import main

import logging

from niceman.utils import swallow_logs
from niceman.tests.utils import assert_in

xeyes_yaml = opj(dirname(__file__), 'files', 'xeyes.yaml')
xeyes_no_x11_yaml = opj(dirname(__file__), 'files', 'xeyes_no_x11-apps.yaml')

def test_diff_same():
    with swallow_logs(new_level=logging.DEBUG) as log:
        args = ['diff', 
                '--env', 
                'niceman/interface/tests/files/xeyes.yaml', 
                '--req', 
                'niceman/interface/tests/files/xeyes_no_x11-apps.yaml'
                ]
        main(args)
        assert_in('requirements satisfied', log.lines)

def test_diff_different():
    with swallow_logs(new_level=logging.DEBUG) as log:
        args = ['diff', 
                '--env', 
                'niceman/interface/tests/files/xeyes_no_x11-apps.yaml', 
                '--req', 
                'niceman/interface/tests/files/xeyes.yaml'
                ]
        main(args)
        assert_in('needed packages: 1', log.lines)
