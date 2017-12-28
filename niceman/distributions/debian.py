# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Support for Debian(-based) distribution(s)."""
import os
from datetime import datetime

import attr
from collections import defaultdict

from six.moves import map

import pytz

from niceman import utils

from email.utils import mktime_tz, parsedate_tz

import logging

# Pick a conservative max command-line
from niceman.support.distributions.debian import \
    parse_apt_cache_show_pkgs_output, parse_apt_cache_policy_pkgs_output, \
    parse_apt_cache_policy_source_info, get_apt_release_file_names, \
    get_spec_from_release_file

try:
    _MAX_LEN_CMDLINE = os.sysconf(str("SC_ARG_MAX")) // 2
except (ValueError, AttributeError):
    _MAX_LEN_CMDLINE = 2048

# To parse output of dpkg-query
import re
_DPKG_QUERY_PARSER = re.compile(
    "(?P<name>[^,:]+)(:(?P<architecture>[^,:]+))?(,.*)?: (?P<path>.*)$"
)

from niceman.distributions.base import DistributionTracer

lgr = logging.getLogger('niceman.distributions.debian')

from .base import SpecObject
from .base import Package
from .base import Distribution
from .base import TypedList
from .base import _register_with_representer
from ..support.exceptions import CommandError
#
# Models
#

# TODO: flyweight/singleton ?
# To make them hashable we need to freeze them... not sure if we are ready:
#@attr.s(cmp=True, hash=True, frozen=True)
@attr.s(cmp=True)
class APTSource(SpecObject):
    """APT origin information
    """
    name = attr.ib()
    component = attr.ib(default=None)
    archive = attr.ib(default=None)
    architecture = attr.ib(default=None)
    codename = attr.ib(default=None)
    origin = attr.ib(default=None)
    label = attr.ib(default=None)
    site = attr.ib(default=None)
    archive_uri = attr.ib(default=None)
    date = attr.ib(default=None)
_register_with_representer(APTSource)


@attr.s(slots=True, frozen=True, cmp=False, hash=True)
class DEBPackage(Package):
    """Debian package information"""
    name = attr.ib()
    # Optional
    upstream_name = attr.ib(default=None)
    version = attr.ib(default=None)
    architecture = attr.ib(default=None)
    source_name = attr.ib(default=None, hash=False)
    source_version = attr.ib(default=None, hash=False)
    size = attr.ib(default=None, hash=False)
    md5 = attr.ib(default=None, hash=False)
    sha1 = attr.ib(default=None, hash=False)
    sha256 = attr.ib(default=None, hash=False)
    versions = attr.ib(default=None, hash=False)  # Hash ver_str -> [Array of source names]
    install_date = attr.ib(default=None, hash=False)
    files = attr.ib(default=attr.Factory(list), hash=False)

    def satisfies(self, other):
        """return True if this package (self) satisfies the requirements of 
        the passed package (other)"""
        if not isinstance(other, Package):
            raise TypeError('satisfies() requires a package argument')
        if not isinstance(other, DEBPackage):
            return False
        if self.name != other.name:
            return False
        if other.version is not None and self.version != other.version:
            return False
        if other.architecture is not None \
                and self.architecture != other.architecture:
            return False
        return True

_register_with_representer(DEBPackage)

@attr.s
class DebianDistribution(Distribution):
    """
    Class to provide Debian-based shell commands.
    """

    apt_sources = TypedList(APTSource)
    packages = TypedList(DEBPackage)
    version = attr.ib(default=None)  # version as depicted by /etc/debian_version

    def initiate(self, session):
        """
        Perform any initialization commands needed in the environment environment.

        Parameters
        ----------
        environment : object
            The Environment sub-class object.
        """
        lgr.debug("Adding Debian update to environment command list.")
        session.execute_command(['apt-get', 'update'])
        #session.execute_command(['apt-get', 'install', '-y', 'python-pip'])
        # session.set_env(DEBIAN_FRONTEND='noninteractive', this_session_only=True)

    def install_packages(self, session, use_version=True):
        """
        Install the packages associated to this distribution by the provenance
        into the environment.

        Parameters
        ----------
        session : object
        use_version : bool, optional
          Use version information if provided.
          TODO: support outside or deprecate
            
        """
        package_specs = []

        for package in self.packages:
            package_spec = package.name
            if use_version and package.version:
                package_spec += '=%s' % package.version
            package_specs.append(package_spec)

        # Doing in one shot to fail early if any of the versioned specs
        # couldn't be satisfied
        lgr.debug("Installing %s", ', '.join(package_specs))
        session.execute_command(
            # TODO: Pull env out of provenance for this command.
            ['apt-get', 'install', '-y'] + package_specs,
            # env={'DEBIAN_FRONTEND': 'noninteractive'}
        )

    def normalize(self):
        # TODO:
        # - among apt-source we could merge some together if we allow for
        #   e.g. component (main, contrib, non-free) to be a list!  but that
        #   would make us require supporting flexible typing -- string or a list
        pass

    def satisfies_package(self, package):
        """return True if this distribution (self) satisfies the requirements 
        of the passed package"""
        if not isinstance(package, Package):
            raise TypeError('satisfies_package() requires a package argument')
        if not isinstance(package, DEBPackage):
            return False
        return any([ p.satisfies(package) for p in self.packages ])

    def satisfies(self, other):
        """return True if this distribution (self) satisfies the requirements 
        of the other distribution (other)"""
        if not isinstance(other, Distribution):
            raise TypeError('satisfies() requires a distribution argument')
        if not isinstance(other, DebianDistribution):
            return False
        return all(map(self.satisfies_package, other.packages))

    def __sub__(self, other):
        # the semantics of distribution subtraction are, for d1 - d2:
        #     what is specified in d1 that is not specified in d2
        #     or how does d2 fall short of d1
        #     or what is in d1 that isn't satisfied by d2
        return [ p for p in self.packages if not other.satisfies_package(p) ]

    # to grow:
    #  def __iadd__(self, another_instance or DEBPackage, or APTSource)
    #  def __add__(self, another_instance or DEBPackage, or APTSource)
    # but for the checks we should get away from a plain "list of" to some
    # structure to help identify on presence

_register_with_representer(DebianDistribution)


class DebTracer(DistributionTracer):
    """.deb-based (and using apt and dpkg) systems package tracer
    """

    # The Debian tracer is not designed to handle directories
    HANDLES_DIRS = False

    # TODO: (Low Priority) handle cases from dpkg-divert
    def _init(self):
        # TODO: we might want a generic helper for collections of things
        # where we could match based on the set of attrs which matter
        self._apt_sources = {}  # dict of source_name -> APTSource
        self._apt_source_names = set()
        self._all_apt_sources = {}
        self._source_line_to_name_map = {}

    def identify_distributions(self, files):
        if not files:
            return
        
        try:
            debian_version = self._session.read('/etc/debian_version').strip()
            self._session.exists('/etc/os-release')
            # for now would also match Ubuntu -- there it would have
            # ID=ubuntu and ID_LIKE=debian
            # TODO: load/parse /etc/os-release into a dict and better use
            # VERSION_ID and then ID (to decide if Debian or Ubuntu or ...)
            _, _ = self._session.execute_command('grep -i "^ID.*=debian"'
                                                     ' /etc/os-release')
            _, _ = self._session.execute_command('ls -ld /etc/apt')
        except CommandError as exc:
            lgr.debug("Did not detect Debian (or derivative): %s", exc)
            return

        packages, remaining_files = self.identify_packages_from_files(files)
        # TODO: add option to report distribution even if no packages/files
        # found association
        if not packages:
            return

        packages = self.get_details_for_packages(packages)

        # TODO: Depending on ID might be debian or ubuntu -- we might want to
        # absorb them all within DebianDistribution or have custom classes??
        # So far they seems to be largely similar
        dist = DebianDistribution(
            name="debian",
            version=debian_version,
            packages=packages,
            # TODO: helper to go from list -> dict based on the name, since must be unique
            apt_sources=list(self._apt_sources.values())
        )  # the one and only!
        dist.normalize()
        #   similar to DBs should take care about identifying/groupping etc
        #   of origins etc
        yield dist, remaining_files

    def _get_packagefields_for_files(self, files):
        file_to_package_dict = {}

        # Find out how many files we can query at once
        max_len = max([len(f) for f in files])
        num_files = max((_MAX_LEN_CMDLINE - 13) // (max_len + 1), 1)

        for subfiles in (files[pos:pos + num_files]
                         for pos in range(0, len(files), num_files)):
            out = self._run_dpkg_query(subfiles)

            # Now go through the output and assign packages to files
            for outline in out.splitlines():
                # Parse package name (architecture) and path
                # TODO: Handle query of /bin/sh better
                outdict = self._parse_dpkgquery_line(outline)
                if not outdict:
                    lgr.debug("Skipping line %s", outline)
                    continue
                # Pull the found path from the dictionary
                found_name = outdict.pop('path')
                if not found_name:
                    raise ValueError(
                        "Record %s got no path defined... skipping"
                        % repr(outdict)
                    )
                # Associate the file to the package name (and architecture)
                pkg = outdict
                lgr.debug("Identified file %r to belong to package %s",
                          found_name, pkg)
                file_to_package_dict[found_name] = pkg
        return file_to_package_dict

    def _get_apt_source_name(self, src):
        # Create a unique name for the origin
        name_fmt = "apt_%s_%s_%s_%%d" % (src.origin or "", src.archive or "",
                                         src.component or "")
        name = utils.generate_unique_name(name_fmt, self._apt_source_names)
        # Remember the created name
        self._apt_source_names.add(name)
        # Create a named origin
        return name

    def get_details_for_packages(self, packages):
        # Find apt sources if not defined
        if not self._all_apt_sources:
            self._find_all_sources()

        # Store the package details as dicts so that we can easily add to them
        pkg_dicts = [attr.asdict(pkg) for pkg in packages]

        # Use dpkg -s <pkg> to get arch and version
        self._get_pkgs_arch_and_version(pkg_dicts)

        # Use apt-cache show <pkg> to get details
        self._get_pkgs_details_from_apt_cache_show(pkg_dicts)

        # Now use "apt-cache policy pkg:arch" to get versions
        self._get_pkgs_versions_and_sources(pkg_dicts)

        # Get install date from the modify time of the dpkg info file
        self._get_pkgs_install_date(pkg_dicts)

        new_packages = []
        for p in pkg_dicts:
            new_pkg = DEBPackage(**p)
            new_packages.append(new_pkg)

        return new_packages

    def _create_package(self, name, architecture=None):

        # Store the details we currently know, we will populate the rest later
        return DEBPackage(
            name=name,
            architecture=architecture,
        )

    def _find_all_sources(self):
        # Use apt-cache policy to get all sources
        out, _ = self._session.execute_command(
            ['apt-cache', 'policy']
        )
        out = utils.to_unicode(out, "utf-8")

        src_info = parse_apt_cache_policy_source_info(out)
        for src_name in src_info:
            src_vals = src_info[src_name]
            date = self._get_date_from_release_file(
                src_vals.get("archive_uri"), src_vals.get("uri_suite"))
            self._all_apt_sources[src_name] = \
                APTSource(
                    name=src_name,
                    component=src_vals.get("component"),
                    codename=src_vals.get("codename"),
                    archive=src_vals.get("archive"),
                    architecture=src_vals.get("architecture"),
                    origin=src_vals.get("origin"),
                    label=src_vals.get("label"),
                    site=src_vals.get("site"),
                    date=date,
                    archive_uri=src_vals.get("archive_uri"))

    def _get_pkgs_arch_and_version(self, pkg_dicts):
        # Convert package names to name:arch format
        queries = []
        for p in pkg_dicts:
            # Use "dpkg -s pkg" to get the installed version and arch
            # Note: "architecture" is in the dict, but may be null
            queries.append(p["name"] if not p["architecture"]
                           else "%s:%s" % (p["name"], p["architecture"]))

        # Find out how many packages we can query at once
        max_len = max([len(q) for q in queries])
        num_queries = max((_MAX_LEN_CMDLINE - 13) // (max_len + 1), 1)

        cmd_results = []
        # Execute dpkg -s, parse, and collate the output
        for subqueries in (queries[pos:pos + num_queries]
                           for pos in range(0, len(queries), num_queries)):
            try:
                out, _ = self._session.execute_command(
                    ['dpkg', '-s'] + subqueries
                )
                out = utils.to_unicode(out, "utf-8")
                # dpkg -s uses the same output as apt-cache show pkg
                cmd_results += parse_apt_cache_show_pkgs_output(out)
            except CommandError as _:
                raise  # Currently raise any exception we encounter

        # Turn dpkg -s results into a lookup table by package name
        cmd_results = self.create_lookup_from_apt_cache_show(cmd_results)

        for p in pkg_dicts:
            # find the version table in the parsed command results for the
            # current package
            r = cmd_results.get(p["name"] if not p["architecture"]
                                else "%s:%s" % (p["name"], p["architecture"]))
            if not r:
                lgr.warning("Was unable to run dpkg -s for %s" %
                            p["name"])
                continue
            # Update the dictionary with found results
            p["architecture"] = r["architecture"]
            p["version"] = r["version"]

    @staticmethod
    def create_lookup_from_apt_cache_show(cmd_results):
        lookup_results = {}
        for r in cmd_results:
            lookup_results[r["package"]] = r
            lookup_results["%s:%s" % (r["package"], r["architecture"])] = r
        return lookup_results

    def _get_pkgs_details_from_apt_cache_show(self, pkg_dicts):
        # Convert package names to name:arch format
        queries = []
        for p in pkg_dicts:
            # Use "dpkg -s pkg" to get the installed version and arch
            queries.append("%s:%s=%s" % (p["name"], p["architecture"],
                                         p["version"]))

        # Find out how many packages we can query at once
        max_len = max([len(q) for q in queries])
        num_queries = max((_MAX_LEN_CMDLINE - 13) // (max_len + 1), 1)

        cmd_results = []
        # Execute dpkg -s, parse, and collate the output
        for subqueries in (queries[pos:pos + num_queries]
                           for pos in range(0, len(queries), num_queries)):
            try:
                out, _ = self._session.execute_command(
                    ['apt-cache', 'show'] + subqueries
                )
                out = utils.to_unicode(out, "utf-8")
                cmd_results += parse_apt_cache_show_pkgs_output(out)
            except CommandError as _:
                raise  # Currently raise any exception we encounter

        # Turn apt-cache show results into a lookup table by package name
        cmd_results = self.create_lookup_from_apt_cache_show(cmd_results)

        for p in pkg_dicts:
            # find the version table in the parsed command results for the
            # current package
            r = cmd_results.get("%s:%s" % (p["name"], p["architecture"]))
            if not r:
                lgr.warning("Was unable to run apt-cache show for %s" %
                            p["name"])
                continue
            # Update the dictionary with found results (if present)
            for f in ("source_name", "source_version", "size", "md5",
                      "sha1", "sha256"):
                if f in r:
                    p[f] = r[f]

    def _get_pkgs_install_date(self, pkg_dicts):
        # Convert package names to dpkg list filenames
        queries = []
        for p in pkg_dicts:
            queries.append(self._pkg_name_to_dpkg_list_file(p["name"]))

        # Find out how many packages we can query at once
        max_len = max([len(q) for q in queries])
        num_queries = max((_MAX_LEN_CMDLINE - 13) // (max_len + 1), 1)

        cmd_results = {}
        # Execute dpkg -s, parse, and collate the output
        for subqueries in (queries[pos:pos + num_queries]
                           for pos in range(0, len(queries), num_queries)):
            try:
                out, _ = self._session.execute_command(
                    ['stat', '-c', '%n: %Y'] + subqueries
                )
            except CommandError as exc:  # file not found
                stderr = utils.to_unicode(exc.stderr, "utf-8")
                if 'No such file or directory' in stderr:
                    out = exc.stdout  # One file not found, so continue
                else:
                    raise  # some other fault -- handle it above
            # Parse the output and store by filename
            for outlines in out.splitlines():
                (fname, ftime) = outlines.split(": ")
                cmd_results[fname] = str(
                    pytz.utc.localize(
                        datetime.utcfromtimestamp(float(ftime))))
        # Now lookup the packages in the results
        for p in pkg_dicts:
            fname = self._pkg_name_to_dpkg_list_file(p["name"])
            if fname in cmd_results:
                p["install_date"] = cmd_results[fname]

    def _pkg_name_to_dpkg_list_file(self, name):
        query = "/var/lib/dpkg/info/" + name + ".list"
        return query

    def _get_pkgs_versions_and_sources(self, pkg_dicts):
        # Convert package names to name:arch format
        queries = []
        for p in pkg_dicts:
            # Use "dpkg -s pkg" to get the installed version and arch
            queries.append("%s:%s" % (p["name"], p["architecture"]))

        # Find out how many packages we can query at once
        max_len = max([len(q) for q in queries])
        num_queries = max((_MAX_LEN_CMDLINE - 13) // (max_len + 1), 1)

        cmd_results = {}
        # Execute dpkg -s, parse, and collate the output
        for subqueries in (queries[pos:pos + num_queries]
                           for pos in range(0, len(queries), num_queries)):
            try:
                out, _ = self._session.execute_command(
                    ['apt-cache', 'policy'] + subqueries
                )
                out = utils.to_unicode(out, "utf-8")
                cmd_results.update(parse_apt_cache_policy_pkgs_output(out))
            except CommandError as _:
                raise  # Currently raise any exception we encounter

        for p in pkg_dicts:
            # find the version table in the parsed command results for the
            # current package (it could be listed by name or name:arch)
            ver = cmd_results.get("%s:%s" % (p["name"], p["architecture"]))
            if not ver:
                ver = cmd_results.get(p["name"])
            if not ver:
                lgr.warning("Was unable to get version table for %s" %
                            p["name"])
                continue

            ver_dict = {}
            for v in ver.get("versions"):
                key = v["version"]
                ver_dict[key] = []
                for s in v.get("sources"):
                    s = s["source"]
                    # If we haven't named the source yet, name it
                    if s not in self._source_line_to_name_map:
                        # Make sure we can find the source
                        if s not in self._all_apt_sources:
                            lgr.warning("Cannot find source %s" % s)
                            continue
                        # Grab and name the source
                        source = self._all_apt_sources[s]
                        src_name = self._get_apt_source_name(source)
                        source.name = src_name
                        # Now add the source to our used sources
                        self._apt_sources[src_name] = source
                        # add the name for easy future lookup
                        self._source_line_to_name_map[s] = src_name
                    # Look up and add the short name for the source
                    ver_dict[key].append(
                        self._source_line_to_name_map[s])
            p["versions"] = ver_dict

    def _get_date_from_release_file(self, archive_uri, uri_suite):
        date = None
        for filename in get_apt_release_file_names(archive_uri, uri_suite):
            try:
                out = self._session.read(filename)
                spec = get_spec_from_release_file(out)
                date = str(pytz.utc.localize(
                    datetime.utcfromtimestamp(
                        mktime_tz(parsedate_tz(spec.date)))))
            except CommandError as _:
                # NOTE: We will be trying release files that end in
                # "Release" and "InRelease", so we expect to fail in opening
                # specific attempts.
                pass
        return date

    def _run_dpkg_query(self, subfiles):
        try:
            out, err = self._session.execute_command(
                ['dpkg-query', '-S'] + subfiles,
                # TODO: what should we do about those additional flags we have
                # in Runner but not yet in execute_command for all sessions
                #expect_stderr=True, expect_fail=True
            )
        except CommandError as exc:
            stderr = utils.to_unicode(exc.stderr, "utf-8")
            if 'no path found matching pattern' in stderr:
                out = exc.stdout  # One file not found, so continue
            else:
                raise  # some other fault -- handle it above
        out = utils.to_unicode(out, "utf-8")
        return out

    @staticmethod
    def _parse_dpkgquery_line(line):
        if line.startswith('diversion '):
            return None  # we are ignoring diversion details ATM  TODO
        if ',' in line:
            lgr.warning("dpkg-query line has multiple packages (%s)" % line)
        res = _DPKG_QUERY_PARSER.match(line)
        if res:
            res = res.groupdict()
            if res['architecture'] is None:
                res.pop('architecture')
        return res
