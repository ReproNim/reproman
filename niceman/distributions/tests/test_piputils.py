# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from niceman.distributions.piputils import parse_pip_show


def test_parse_pip_show():
    out_base = """\
Name: pkg
Version: 0.3.0
Summary: foo
Home-page: https://github.com/ReproNim/niceman/
Author: marty
Author-email: marty@nowhere
License: GPL3
Location: /local/path/to/site-packages
Requires: six, funcsigs
"""

    # Check parsing of show output for a "standard" package.
    out_files = out_base + """\
Files:
  pkg-0.3.0.dist-info/DESCRIPTION.rst
  pkg/__init__.py"""
    info_files = parse_pip_show(out_files)

    fields = {"Name", "Version", "Summary", "Home-page", "Author",
              "Author-email", "License", "Location", "Requires", "Files"}

    assert set(info_files.keys()) == fields
    assert info_files["License"] == "GPL3"
    assert info_files["Files"] == ["pkg-0.3.0.dist-info/DESCRIPTION.rst",
                                   "pkg/__init__.py"]

    # Check parsing of show output for an editable packages that lacks
    # files.
    out_no_files = out_base + """\
Files:
Cannot locate installed-files.txt"""
    info_nofiles = parse_pip_show(out_no_files)
    assert set(info_nofiles.keys()) == fields
    assert info_nofiles["Files"] == []
