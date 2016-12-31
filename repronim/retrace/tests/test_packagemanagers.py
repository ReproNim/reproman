# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
from pprint import pprint

from repronim.retrace.packagemanagers import identify_packages


def test_identify_packages():
    files = ["/usr/share/doc/xterm/copyright",
             "/usr/share/icons/hicolor/48x48/apps/xterm-color.png",
             "/usr/bin/vim.basic",
             "/usr/share/bug/vim/script",
             "/home/butch"]
    files, packages = identify_packages(files)
    pprint(files)
    pprint(packages)
    assert True
