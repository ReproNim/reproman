# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to identify package sources for files"""

from __future__ import unicode_literals

import os

from collections import OrderedDict
from os.path import dirname, isdir, isabs
from os.path import exists, lexists
from os.path import join as opj

from logging import getLogger
from six import viewvalues

from niceman.dochelpers import exc_str
from niceman.utils import only_with_values

try:
    import apt
    import apt.utils as apt_utils
    import apt_pkg
    cache = apt.Cache()
except ImportError:
    apt = None
    apt_utils = None
    apt_pkg = None
    cache = None

from niceman.cmd import Runner
from niceman.cmd import CommandError

lgr = getLogger('niceman.api.retrace')

from .packagemanagers import PackageManager


class VCSRepo(object):
    """Base VCS repo class"""

    def __init__(self, path):
        """Representation for a repository

        Parameters
        ----------
        path: str
           Path to the top of the repository

        """
        self.path = path


class GitSVNRepo(VCSRepo):
    """apparently for now the way to figure out files is similar

    Might later become a mix-in class for any VCS having such "feature" as
    listing files for a repo
    """

    _ls_files_command = None  # just need to define in subclass
    _ls_files_filter = None

    def __init__(self, path):
        """Representation for Git or SVN repository

        Parameters
        ----------
        path: str
           Path to the top of the repository

        """
        super(GitSVNRepo, self).__init__(path)
        self._files = None
        self._runner = Runner(env={'LC_ALL': 'C'}, cwd=self.path)

    @property
    def files(self):
        if self._files is None:
            out, err = self._runner(self._ls_files_command)
            assert not err
            self._files = set(filter(None, out.split('\n')))
            if self._ls_files_filter:
                self._files = self._ls_files_filter(self._files)
        return self._files

    def is_mine(self, path):
        # does this repository have this directory under its control?
        # NOTE:
        #  this is an interesting case -- don't we want to still track "possible"
        #  artifacts produced from the repos?  e.g. ./build subdirectory
        #  But for that we would need to ask twice -- first a full sweep across
        #  all Resolvers making it all strict checks, and then again through
        #  those which could potentially claim it to belong to the repo?
        #  For now just a strict check, and we would want to request all files
        #  which repo knows about
        rpath = path[len(self.path)+1:]
        return rpath in self.files

    @classmethod
    def get_at_dirpath(cls, dirpath):
        raise NotImplementedError

# Name must be   TYPERepo since used later in the code
# As an overkill might want some metaclass to look after that ;-)
class SVNRepo(GitSVNRepo):

    @property
    def _ls_files_command(self):
        # tricky -- we need to locate wc.db somewhere upstairs, and filter out paths
        root_path = self._info['Working Copy Root Path']
        return 'sqlite3 -batch %s/.svn/wc.db ".headers off" ' \
            '"select local_relpath from nodes_base"' \
                    % root_path

    def _ls_files_filter(self, all_files):
        root_path = self._info['Working Copy Root Path']
        subdir = os.path.relpath(self.path, root_path)
        if subdir == os.curdir:
            return all_files
        else:
            return [f[len(subdir)+1:] for f in all_files
                    if os.path.commonprefix((subdir, f)) == subdir]

    def __init__(self, *args, **kwargs):
        super(SVNRepo, self).__init__(*args, **kwargs)
        self.__info = None

    @classmethod
    def get_at_dirpath(cls, dirpath):
        # ho ho -- no longer the case that there is .svn in each subfolder:
        # http://stackoverflow.com/a/9070242
        found = False
        if exists(opj(dirpath, '.svn')):  # early detection
            found = True
        # but still might be under SVN
        if not found:
            try:
                out, err = Runner(cwd=dirpath).run(
                    'svn info',
                    expect_fail=True)
            except CommandError as exc:
                if "Please see the 'svn upgrade' command" in exc.message:
                    lgr.warning(
                        "SVN at %s is outdated, needs 'svn upgrade'",
                        dirpath)
                else:
                    # we are in SVN but it is outdated and needs an upgrade
                    lgr.debug(
                        "Probably %s is not under SVN repo path: %s",
                        dirpath, exc_str(exc)
                    )
                    return None
        # for now we treat each directory under SVN independently
        # pros:
        #   - could provide us 'minimal' set of checkouts to do, since it might be
        #      quite expensive to checkout the entire tree if it was not used
        #      besides few leaves
        lgr.debug("Detected SVN repository at %s", dirpath)
        return cls(dirpath)

    @property
    def _info(self):
        if self.__info is None:
            # TODO -- outdated repos might need 'svn upgrade' first
            # so not sure -- if we should copy them somewhere first and run
            # update there or ask user to update them on his behalf?!
            out, err = self._runner('svn info')
            self.__info = dict([x.lstrip() for x in l.split(':', 1)] for l in out.splitlines() if l.strip())
        return self.__info

    @property
    def version(self):
        return self._info['Revision']

    @property
    def semantic_version(self):
        """Let's use git describe"""
        return None

    @property
    def sources(self):
        # also has similarity to APT in that we could have the top of SVN repo
        # as an 'origin' which might be reused by multiple 'sub-repos'/directories
        # "Repository Root" and "Relative URL"
        return self._info['URL']


class GitRepo(GitSVNRepo):
    _ls_files_command = 'git ls-files'

    @classmethod
    def get_at_dirpath(cls, dirpath):
        try:
            out, err = Runner(cwd=dirpath).run(
                'git rev-parse --show-toplevel',
                expect_fail=True)
        except CommandError as exc:
            lgr.debug(
                "Probably %s is not under git repo path: %s",
                dirpath, exc_str(exc)
            )
            return None
        topdir = out.rstrip('\n')
        lgr.debug("Detected Git repository at %s for %s", topdir, dirpath)
        return cls(topdir)

    @property
    def version(self):
        return self._runner.run('git rev-parse HEAD')[0].strip()
        
    @property
    def semantic_version(self):
        """Let's use git describe"""
        try:
            return self._runner('git describe --tags', expect_fail=True)[0].strip()
        except CommandError:
            return None

    @property
    def sources(self):
        # ideally needs to figure out the remote(s) which already have
        # this commit.  So kinda similar to APT where we list all origins
        # where some might not even contain current version
        return "TODO"


class VCSManager(PackageManager):
    """Resolve files into Git repositories they are contained with

    TODO: generalize to other common VCS (svn, hg, bzr) which should win one
    over the other depending on the path, e.g. for path

    Devel notes:
    - Whenever we allow for some "hypothetical" ownership, /a/b/c/d/f with
      git at /a/b and hg at /a/b/c/ it must be hg repo which contains it.
      But may be we wouldn't need that and should just grab all the repositories
      for which we have strict membership hits, and then all possible which sit
      above files which were not found belonging to any -- that is where we
      could go with the most nested one and include it as well, although without
      assigning any file specifically to it
    - CVS and svn might be the first ones to consider since they have corresponding
      .svn and CVS at every level in their hierarchy so easier to catch

    Assumptions:
    - VCS operate at the "directories" level, i.e. the file /a/b/c can't be contained
      in one VCS whenever /a/b/d file in another
    """

    REGISTERED_VCS = (SVNRepo, GitRepo)

    def __init__(self, *args, **kwargs):
        super(VCSManager, self).__init__(*args, **kwargs)
        # dictionary to contain per each inspected/known directory a VCS
        # instance it belongs to
        self._known_repos = {}

    def _create_package(self, vcs):
        # prep our pkg object:
        pkg = OrderedDict()
        pkg["path"] = vcs.path
        pkg["type"] = vcs.__class__.__name__[:-4].lower()   # strip Repo
        # VCS specific ways to identify the version, sources, etc
        pkg["version"] = vcs.version
        pkg["semantic_version"] = vcs.semantic_version
        pkg["sources"] = vcs.sources
        # TODO:  we might want to mark those which are found to belong to pkg
        #  files which are dirty.
        # pkg["dirty"]
        pkg = only_with_values(pkg)
        pkg["files"] = []
        return pkg


    def resolve_file(self, path):
        """Given a path, return path of the repository it belongs to"""
        # very naive just to get a ball rolling
        if not isabs(path):
            raise ValueError("ATM operating on full paths, got %s" % path)
        dirpath = path if isdir(path) else dirname(path)

        # quick check first
        if dirpath in self._known_repos:
            return self._known_repos[dirpath]

        # it could still be a subdirectory known to the repository known above it
        for repo in self._known_repos.values():
            # XXX this design is nohow accounts for some fancy cases where
            # someone could use GIT_TREE and other trickery to have out of the
            # directory checkout.  May be some time we would get there but
            # for now
            # should be ok

            # could be less efficient than some str manipulations but ok for now
            if os.path.commonprefix((repo.path, path)) != repo.path:
                continue

            # could be less efficient than some str manipulations but ok for now
            # since we rely on a strict check (must be registered within the repo)
            if repo.is_mine(path):
                return repo

        # ok -- if it is not among known repos, we need to 'sniff' around
        # if there is a repository at that path
        for VCS in self.REGISTERED_VCS:
            lgr.log(5, "Trying %s for path %s", VCS, path)
            vcs = VCS.get_at_dirpath(dirpath) if lexists(dirpath) else None
            if vcs:
                # so there is one nearby -- record it
                self._known_repos[vcs.path] = vcs
                # but it might still not to know about the file
                if vcs.is_mine(path):
                    return vcs
                # if not -- just keep going to the next candidate repository
        return None

    def _get_packages_for_files(self, files):
        return {f: self.resolve_file(f) for f in files}

    def identify_package_origins(self, *args, **kwargs):
        # no origins for any VCS AFAIK
        return None