# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import mock

from niceman.distributions import piputils
from niceman.tests.utils import assert_is_subset_recur


def test_pip_batched_show():
    pkgs = ["pkg0", "pkg1", "pkg2"]
    batches= [("""\
Name: pkg0
Version: 4.1
Home-page: urlwith---three-dashes
Files:
  file0
---
Name: pkg1
Version: 17.4.0
Files:
  file1""",
              None, None),  # err, exception
             ("""\
Name: pkg2
Version: 4""",
              None, None)]

    with mock.patch("niceman.distributions.piputils.execute_command_batch",
                    return_value=batches):
        pkg_entries = list(piputils._pip_batched_show(None, None, pkgs))

    expect = [("pkg0",
               {"Name": "pkg0", "Version": "4.1", "Files": ["file0"],
                # We did not split on the URL's "---".
                "Home-page": "urlwith---three-dashes"}),
              ("pkg1",
               {"Name": "pkg1", "Version": "17.4.0", "Files": ["file1"]}),
              ("pkg2",
               {"Name": "pkg2", "Version": "4"})]
    assert_is_subset_recur(expect, pkg_entries, [dict, list])


def test_parse_pip_show():
    out_base = """\
Name: pkg
Version: 0.3.0
Summary: foo
# Comment line
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
    info_files = piputils.parse_pip_show(out_files)

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
    info_nofiles = piputils.parse_pip_show(out_no_files)
    assert set(info_nofiles.keys()) == fields
    assert info_nofiles["Files"] == []
