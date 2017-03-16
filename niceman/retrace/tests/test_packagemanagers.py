# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import os
import mock
from pprint import pprint

from niceman.retrace.packagemanagers import identify_packages
from niceman.retrace.packagemanagers import DpkgManager


def test_identify_packages():
    files = ["/usr/share/doc/xterm/copyright",
             "/usr/games/alienblaster",
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


def test_find_release_file():


    fp = lambda p: os.path.join('/var/lib/apt/lists', p)

    def mocked_exists(path):
        return path in {
            fp('s_d_d_data_crap_InRelease'),
            fp('s_d_d_datas_InRelease'),
            fp('s_d_d_data_InRelease'),
            fp('s_d_d_sid_InRelease'),
            fp('s_d_d_InRelease')
        }

    with mock.patch('os.path.exists', mocked_exists):
        assert DpkgManager._find_release_file(
            fp('s_d_d_data_non-free_binary-amd64_Packages')) == \
                fp('s_d_d_data_InRelease')
        assert DpkgManager._find_release_file(
            fp('s_d_d_data_non-free_binary-i386_Packages')) == \
                fp('s_d_d_data_InRelease')
        assert DpkgManager._find_release_file(
            fp('oths_d_d_data_non-free_binary-i386_Packages')) is None
