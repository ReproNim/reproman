# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Utilities for working with pip.
"""
import re


def parse_pip_show(out):
    pip_info = {}
    list_tag = None
    for line in out.splitlines():
        if line.startswith("#"):   # Skip if comment
            continue
        if line.startswith("  "):  # List item
            item = line[2:].strip()
            if list_tag and item:  # Add the item to the existing list
                pip_info[list_tag].append(item)
            continue
        if ":" in line:            # List tag or tag/value
            split_line = line.split(":", 1)
            tag = split_line[0].strip()
            value = None
            if len(split_line) > 1:  # Parse the value if there
                value = split_line[1].strip()
            if value:                # We have both a tag and a value
                pip_info[tag] = value
                list_tag = None      # A new tag stops the previous list
            else:                    # We have just a list_tag so start it
                list_tag = tag
                pip_info[list_tag] = []

    return pip_info


def parse_pip_list(out):
    """Parse the output of `pip list --format=legacy`.

    Parameters
    ----------
    out : string
        Output of `pip list --format=legacy`.

    Returns
    -------
    A generator that yields (name, version, location) for each
    package.  Location will be None unless the package is editable.
    """
    pkg_re = re.compile(r"^([^(]+) \((.+)\)$", re.MULTILINE)
    for pkg, version_location in pkg_re.findall(out):
        if "," in version_location:
            version, location = version_location.split(", ")
        else:
            version = version_location
            location = None
        yield pkg, version, location
