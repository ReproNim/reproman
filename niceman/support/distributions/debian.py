# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Various supporting utilities for Debian(-based) distributions

"""

from __future__ import absolute_import

import logging
import re
import string

import attr

from niceman.utils import attrib

lgr = logging.getLogger('niceman.distributions.debian')

__docformat__ = 'restructuredtext'


@attr.s
class DebianReleaseSpec(object):
    """Encapsulates knowledge about used Debian release

    origin: Debian
    label: Debian
    suite: stable
    version: 8.5
    codename: jessie
    date: Sat, 04 Jun 2016 13:24:54 UTC
    components: main contrib non-free
    architectures: amd64
    """

    # Those could be different in overlays or other derived distributions
    origin = attrib(default=attr.NOTHING)   # Debian
    label = attrib(default=attr.NOTHING)    # Debian
    codename = attrib(default=attr.NOTHING)
    suite = attrib(default=attr.NOTHING)
    version = attrib(default=attr.NOTHING)
    date = attrib(default=attr.NOTHING)
    components = attrib(default=attr.NOTHING)
    architectures = attrib(default=attr.NOTHING)


def get_spec_from_release_file(content):
    """Provide specification object describing the component of the distribution
    """
    # RegExp to pull a single line "tag: value" pair from a deb822 file
    re_deb822_single_line_tag = re.compile("""
        ^(?P<tag>[a-zA-Z][^:]*):[\ ]+  # Tag - begins at start of line
        (?P<val>\S.*)$           # Value - after colon to the end of the line
    """, flags=re.VERBOSE + re.MULTILINE)

    # Split before PGP signature if present
    content = content.split("-----BEGIN PGP SIGNATURE-----")[0]

    # Parse the content for tags and values into a dictionary
    release = {
        match.group("tag"): match.group("val")
        for match in re_deb822_single_line_tag.finditer(content)
    }

    # TODO: redo with conversions of components and architectures in into lists
    # and date in machine-readable presentation
    return DebianReleaseSpec(**{
        a.name: release.get(a.name.title(), None)
        for a in attr.fields(DebianReleaseSpec)
        })


def parse_apt_cache_show_pkgs_output(output):
    package_info = []
    # Split into entries (one per package)
    entries = filter(bool, re.split('\n(?=Package:)', output,
                                    flags=re.MULTILINE))

    # RegExp to pull a single line "tag: value" pair from a deb822 file
    re_deb822_single_line_tag = re.compile("""
        ^(?P<tag>[a-zA-Z][^:]*):[\ ]+  # Tag - begins at start of line
        (?P<val>\S.*)$           # Value - after colon to the end of the line
    """, flags=re.VERBOSE + re.MULTILINE)
    # RegExp to split source into source and version
    re_source = re.compile("""
        ^(?P<source_name>[^ ]+)                # source name before any space
        ([^(]*\((?P<source_version>[^)]+)\))?  # source version in parentheses
    """, flags=re.VERBOSE)

    # For each package entry, collect single line tag/value pairs into a
    # dictionary
    for entry in entries:
        pkg = {
           match.group("tag").lower(): match.group("val")
           for match in re_deb822_single_line_tag.finditer(entry)
        }
        # Process the package if one was found
        if "package" in pkg:
            # Parse source line to get source version (if present)
            if "source" in pkg:
                for match in re_source.finditer(pkg["source"]):
                    pkg["source_name"] = match.group("source_name")
                    pkg["source_version"] = match.group("source_version")
            # Move md5sum to md5
            pkg["md5"] = pkg.pop("md5sum", None)
            # Append package entry
            package_info.append(pkg)
    return package_info


def parse_apt_cache_policy_pkgs_output(output):
    # findall wasn't greedy enough for some reason, so decided first to
    # split into entries (one per package)
    entries = filter(bool, re.split('\n(?=\S)', output, flags=re.MULTILINE))
    # now we need to parse/match each entry
    re_pkg = re.compile("""
        ^(?P<name>[^\s:]+):((?P<architecture>\S+):)?\s*\n  # package name
        \s+Installed:\s*(?P<installed>\S*)\s*\n    # Installed version
        \s+Candidate:\s*(?P<candidate>\S*)\s*\n    # Candidate version
        \s+Version\stable:[^\n]*
        (?P<version_table>(\n\s.*)+)
        """, flags=re.VERBOSE)

    re_versions = re.compile("""
        ^(\s{5}|\s(?P<installed>\*\*\*)\s)
        (?P<version>\S+)\s+
        (?P<priority>\S+)\n.*
        (?P<sources>(\n\s{8}.*)+)
    """, flags=re.VERBOSE + re.MULTILINE)
    re_source = re.compile("""
        ^\s{8}(?P<priority>\S+)\s+
        (?P<source>.*)$
    """, flags=re.VERBOSE + re.MULTILINE)
    pkgs = {}
    for entry in entries:
        match = re_pkg.match(entry.strip())
        if not match:
            lgr.warning("FAILED in %s " % entry)
            continue
        info = match.groupdict()
        pkgs[info.pop('name')] = info
        info['versions'] = []
        for version in re_versions.finditer(info.pop('version_table')):
            version_dict = version.groupdict()
            version_dict["sources"] = [
                source.groupdict()
                for source in re_source.finditer(version.group("sources"))
                ]
            info['versions'].append(version_dict)
        # process version_table
    return pkgs
    #for pkg_match in re_pkg.finditer(output):
    #    print type(pkg_match), pkg_match.groupdict()


def parse_apt_cache_policy_source_info(policy_output):
    source_info = {}
    re_section = re.compile("""
        ^(?P<header_line>\S.*)$[\r\n]*  # Header - non whitespace at the
                                        #          beginning of the line
        (?P<body>(^\ .*$[\r\n]*)*)      # Body - All subsequent lines that
                                        #        begin with a space
        """, flags=re.VERBOSE + re.MULTILINE)
    re_source = re.compile("""
        ^(\ (?P<priority>[0-9]+)\ +(?P<source>.*)$[\r\n]+
         (^(
            (\ \ +release\ +(?P<release_info>.*))|
            (\ \ +origin\ +(?P<origin_info>.*))|
            (\ \ .*)
           )$[\r\n]+
          )*
        )
        """, flags=re.VERBOSE + re.MULTILINE)
    re_rel_attrib = re.compile("""
        (?P<tag>[a-z])=    # A tag is a single letter followed by "="
        (?P<value>([^,]|(,(?![a-z]=)))*)
                           # The value follows the "=", and include any
                           # non commas, or commas not followed by another tag
        """, flags=re.VERBOSE)
    re_source_line = re.compile("""
        (?P<archive_uri>\S+)        # Archive URI up to the first " "
        (\ (?P<uri_suite>[^/]+))?   # The suite goes up to the first "/"
        """, flags=re.VERBOSE)
    # The release line has a terse tag=value format. This maps
    # the release tags to more meaningful values
    tag_map = {"c": "component",
               "n": "codename",
               "a": "archive",
               "b": "architecture",
               "o": "origin",
               "l": "label"}

    sections = re_section.finditer(policy_output)
    for section in sections:
        if section.group("header_line").startswith("Package files:"):
            sources = re_source.finditer(section.group("body"))
            for source in sources:
                info = source.groupdict()
                if info.get("source"):
                    src_detail = dict()
                    src_detail["site"] = info.get("origin_info")
                    match = re_source_line.search(info.get("source"))
                    if match:
                        match = match.groupdict()
                        src_detail["archive_uri"] = match["archive_uri"]
                        src_detail["uri_suite"] = match["uri_suite"]
                    else:
                        lgr.warning("Unexpected source line %s" %
                                    info.get("source"))
                    release_info = info.get("release_info")
                    if release_info:
                        attribs = re_rel_attrib.finditer(release_info)
                        for attrib in attribs:
                            if attrib.group("tag") in tag_map:
                                src_detail[tag_map[attrib.group("tag")]] = \
                                    attrib.group("value")
                    source_info[info.get("source")] = src_detail
    return source_info


def get_apt_release_file_names(url, url_suite):
    url = url.strip("/")              # Remove any trailing /
    url = url.replace("http://", "")  # Remove leading http://
    url = url.replace("file:/", "_")  # file:/ is converted to single _
    url = url.replace("/", "_")       # Any other / becomes _
    if url_suite:
        filename = url + "_dists_" + url_suite
    else:
        filename = url
    return ["/var/lib/apt/lists/" + filename + "_Release",
            "/var/lib/apt/lists/" + filename + "_InRelease"]


def parse_dpkgquery_line(line):
    result_re = re.compile(
        "(?P<name>[^,:]+)(:(?P<architecture>[^,:]+))?(?P<pkgs_rest>,.*)?:"
        " (?P<path>.*)$"
    )
    if line.startswith('diversion '):
        return None  # we are ignoring diversion details ATM  TODO

    res = result_re.match(line)
    if res:
        res = res.groupdict()
        if res['architecture'] is None:
            res.pop('architecture')
    return res
