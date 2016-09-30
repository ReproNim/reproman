# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.cmdline.main import main

import os
from os.path import dirname, abspath

def test_install_main():
    """
    Install two packages locally: base-files and bash
    """
    testfile = dirname(abspath(__file__)) + os.path.sep + 'sample_reprozip_output_small.yml'
    main(['install', '--spec', testfile, '--platform', 'localhost'])

