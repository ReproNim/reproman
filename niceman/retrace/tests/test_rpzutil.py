# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import io
import os

import niceman.retrace.rpzutil as rpzutil


REPROZIP_SPEC_YML_FILENAME = os.path.join(os.path.dirname(__file__), os.pardir,
                                          os.pardir, 'tests', 'files',
                                          'reprozip_xeyes.yml')


def test_load_config():
    config = rpzutil.load_config(REPROZIP_SPEC_YML_FILENAME)
    files_all = rpzutil.get_files(config)
    files_noother = rpzutil.get_files(config, other_files=False)
    assert len(files_noother) < len(files_all)
    output = io.StringIO()
    rpzutil.write_config(output, config)
    assert True
