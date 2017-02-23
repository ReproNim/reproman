# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import lexists
from os.path import join as opj, pardir, dirname

from pprint import pprint

from niceman.retrace.packagemanagers import identify_packages
from niceman.tests.utils import skip_if

def test_identify_packages():
    files = ["/usr/share/doc/xterm/copyright",
             "/usr/share/icons/hicolor/48x48/apps/xterm-color.png",
             "/usr/share/doc/zlib1g/copyright",
             "/usr/bin/vim.basic",
             "/usr/share/bug/vim/script",
             "/home/butch"]
    # TODO: Mock I/O and detect correct analysis
    packages, origins, files = identify_packages(files)
    pprint(files)
    pprint(origins)
    pprint(packages)
    assert True


@skip_if(not lexists(opj(dirname(__file__), pardir, pardir, pardir, '.git')))
def test_identify_myself():
    packages, origins, files = identify_packages([__file__, '/nonexisting-for-sure'])
    assert len(packages) == 1
    assert packages[0]['type'] == 'git'
    assert packages[0]['files'] == [__file__]

    assert files == ['/nonexisting-for-sure']