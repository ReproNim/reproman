# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Support for Debian(-based) distribution(s)."""
import copy
import os
from datetime import datetime

import attr
import collections

import pytz
import yaml

from niceman import utils
from .base import Distribution

import logging

# ??? In principle apt is relevant only for tracing and here we are
#     trying to collect everything Debian related, so it might not event
#     need apt
try:
    import apt
    import apt.utils as apt_utils
    import apt_pkg
    apt_cache = apt.Cache()
except ImportError:
    apt = None
    apt_utils = None
    apt_pkg = None
    apt_cache = None

# Pick a conservative max command-line
try:
    _MAX_LEN_CMDLINE = os.sysconf(str("SC_ARG_MAX")) // 2
except (ValueError, AttributeError):
    _MAX_LEN_CMDLINE = 2048


from niceman.distributions.base import PackageTracer
from niceman.support.exceptions import CommandError

lgr = logging.getLogger('niceman.distributions.debian')


class DebianDistribution(Distribution):
    """
    Class to provide Debian-based shell commands.
    """

    def __init__(self, provenance):
        """
        Class constructor

        Parameters
        ----------
        provenance : dictionary
            Provenance information for the distribution.
        """
        super(DebianDistribution, self).__init__(provenance)

    def initiate(self, environment):
        """
        Perform any initialization commands needed in the environment environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        lgr.debug("Adding Debian update to environment command list.")
        environment.add_command(['apt-get', 'update'])
        environment.add_command(['apt-get', 'install', '-y', 'python-pip'])

    def install_packages(self, environment):
        """
        Install the packages associated to this distribution by the provenance
        into the environment.

        Parameters
        ----------
        environment : object
            Environment sub-class instance.
        """
        for package in self._provenance['packages']:
            environment.add_command(
                # TODO: Pull env out of provenance for this command.
                ['apt-get', 'install', '-y', package['name']],
                # env={'DEBIAN_FRONTEND': 'noninteractive'}
            )


# TODO: flyweight/singleton ?
@attr.s
class APTSource(object):
    """APT origin information
    """
    name = attr.ib()
    component = attr.ib()
    archive = attr.ib()
    architecture = attr.ib()
    codename = attr.ib()
    origin = attr.ib()
    label = attr.ib()
    site = attr.ib()
    archive_uri = attr.ib()
    date = attr.ib()

    @staticmethod
    def yaml_representer(dumper, data):
        ordered_items = attr.asdict(
            data, dict_factory=collections.OrderedDict).items()
        return dumper.represent_mapping('tag:yaml.org,2002:map', ordered_items)

yaml.SafeDumper.add_representer(APTSource, APTSource.yaml_representer)


class DebTracer(PackageTracer):
    """.deb-based (and using apt and dpkg) systems package tracer
    """

    # TODO: (Low Priority) handle cases from dpkg-divert

    def identify_package_origins(self, packages):
        used_names = set()  # Set to avoid duplicate origin names
        unnamed_origin_map = {}  # Map unnamed origins to named origins

        # Iterate over all package origins
        for p in packages:
            for v in p.get("version_table", []):
                for i, o in enumerate(v.get("origins", [])):
                    # If we haven't seen this origin before, generate a
                    # name for it
                    if o not in unnamed_origin_map:
                        unnamed_origin_map[o] = \
                            self._create_named_origin(o, used_names)
                    # Now replace the package origin with the name of the
                    # yaml-prepared origin
                    v["origins"][i] = unnamed_origin_map[o].name

        # Sort the origins by the name for the configuration file
        origins = sorted(unnamed_origin_map.values(), key=lambda k: k.name)

        return origins

    @staticmethod
    def _create_named_origin(o, used_names):
        # Create a unique name for the origin
        name_fmt = "apt_%s_%s_%s_%%d" % (o.origin, o.archive,
                                         o.component)
        name = utils.generate_unique_name(name_fmt,
                                          used_names)
        # Remember the created name
        used_names.add(name)
        # Create a named origin
        new_o = copy.deepcopy(o)
        new_o.name = name
        return new_o

    def _get_packagenames_for_files(self, files):
        file_to_package_dict = {}

        # Find out how many files we can query at once
        max_len = max([len(f) for f in files])
        num_files = max((_MAX_LEN_CMDLINE - 13) // (max_len + 1), 1)

        for subfiles in (files[pos:pos + num_files]
                         for pos in range(0, len(files), num_files)):
            try:
                out, err = self._environ(
                    ['dpkg-query', '-S'] + subfiles,
                    expect_stderr=True, expect_fail=True
                )
            except CommandError as exc:
                stderr = utils.to_unicode(exc.stderr, "utf-8")
                if 'no path found matching pattern' in stderr:
                    out = exc.stdout  # One file not found, so continue
                else:
                    raise  # some other fault -- handle it above

            out = utils.to_unicode(out, "utf-8")

            # Now go through the output and assign packages to files
            for outline in out.splitlines():
                # Note, we must split after ": " instead of ":" in case the
                # package name includes an architecture (like "zlib1g:amd64")
                # TODO: Handle query of /bin/sh better
                (pkg, found_name) = outline.split(': ', 1)
                lgr.debug("Identified file %r to belong to package %s",
                          found_name, pkg)
                file_to_package_dict[found_name] = pkg

        return file_to_package_dict

    def _create_package(self, pkgname):
        if not apt_cache:
            return None
        try:
            pkg_info = apt_cache[pkgname]
        except KeyError:  # Package not found
            return None

        # prep our pkg object:
        pkg = collections.OrderedDict()
        pkg["name"] = pkgname
        pkg["type"] = "dpkg"
        pkg["version"] = pkg_info.installed.version
        pkg["candidate"] = pkg_info.candidate.version
        pkg["size"] = pkg_info.installed.size
        pkg["architecture"] = pkg_info.installed.architecture
        pkg["md5"] = pkg_info.installed.md5
        pkg["sha1"] = pkg_info.installed.sha1
        pkg["sha256"] = pkg_info.installed.sha256
        if pkg_info.installed.source_name:
            pkg["source_name"] = pkg_info.installed.source_name
            pkg["source_version"] = pkg_info.installed.source_version
        pkg["files"] = []

        # Now get installation date
        try:
            pkg["install_date"] = str(
                pytz.utc.localize(
                    datetime.utcfromtimestamp(
                        os.path.getmtime(
                            "/var/lib/dpkg/info/" + pkgname + ".list"))))
        except OSError:  # file not found
            pass

        # Compile Version Table
        pkg_versions = []
        for v in pkg_info.versions:
            v_info = {"version": v.version}
            origins = []
            for (pf, _) in v._cand.file_list:
                # Get the archive uri
                indexfile = v.package._pcache._list.find_index(pf)
                if indexfile:
                    archive_uri = indexfile.archive_uri("")
                else:
                    archive_uri = None

                # Get the release date
                rdate = self._find_release_date(
                    self._find_release_file(pf.filename))

                # Pull origin information from package file
                origin = APTSource(name=None,
                                   component=pf.component,
                                   codename=pf.codename,
                                   archive=pf.archive,
                                   architecture=pf.architecture,
                                   origin=pf.origin,
                                   label=pf.label,
                                   site=pf.site,
                                   archive_uri=archive_uri,
                                   date=rdate)

                # Now add our crafted origin to the list
                origins.append(origin)
            v_info["origins"] = origins
            pkg_versions.append(v_info)

        pkg["version_table"] = pkg_versions

        lgr.debug("Found package %s", pkg)
        return pkg

    @staticmethod
    def _find_release_file(packages_filename):
        # The release filename is a substring of the package
        # filename (excluding the ending "Release" or "InRelease"
        # The split between the release filename and the package filename
        # is at an underscore, so split the package filename
        # at underscores and test for the release file:
        rfprefix = packages_filename
        assert os.path.isabs(packages_filename), \
            "must be given full path, got %s" % packages_filename
        while "_" in rfprefix:
            rfprefix = rfprefix.rsplit("_", 1)[0]
            for ending in ['_InRelease', '_Release']:
                release_filename = rfprefix + ending
                if os.path.exists(release_filename):
                    return release_filename
        # No file found
        return None

    @staticmethod
    def _find_release_date(rfile):
        # Extract and format the date from the release file
        rdate = None
        if rfile:
            rdate = apt_utils.get_release_date_from_release_file(rfile)
            if rdate:
                rdate = str(pytz.utc.localize(
                    datetime.utcfromtimestamp(rdate)))
        return rdate

