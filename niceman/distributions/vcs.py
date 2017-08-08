# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to identify VCS repos for files"""

from __future__ import unicode_literals

import abc
import attr
import os

from collections import defaultdict
from os.path import dirname, isdir, isabs
from os.path import exists, lexists
from os.path import join as opj

from logging import getLogger
from six import viewvalues

from niceman.dochelpers import exc_str
from niceman.utils import only_with_values
from niceman.utils import instantiate_attr_object

from niceman.cmd import Runner
from niceman.cmd import CommandError

lgr = getLogger('niceman.distributions.vcs')

from niceman.distributions.base import DistributionTracer
from niceman.distributions.base import SpecObject
from niceman.distributions.base import Distribution
from niceman.distributions.base import TypedList


# # TODO: use metaclass I guess... ?
# def get_vcs_distribution(RepoClass, name, Name):
#     """A helper to generate VCS distribution classes"""
#     class VCSDistribution(Distribution):
#
#         repositories = TypedList(RepoClass)
#
#         def __init__(self, *args, **kwargs):
#             self.name = name
#             super(VCSDistribution, self).__init__(*args, **kwargs)
#     VCSDistribution.__name__ = str('%sDistribution' % Name)
#     return VCSDistribution


# We need a concept of Distribution
@attr.s
class VCSDistribution(Distribution):
    """
    Base class for VCS "distributions"
    """

    def initiate(self, session):
        # This is VCS specific, but we could may be make it
        # to verify that some executable is available
        session.execute_command(self._cmd)

    @abc.abstractmethod
    def install_packages(self, session, use_version=True):
        # This is VCS specific
        raise NotImplementedError()

    def normalize(self):
        pass


@attr.s
class VCSRepo(SpecObject):
    """Base VCS repo class"""

    path = attr.ib()
    files = attr.ib(default=attr.Factory(list))


@attr.s
class GitRepo(VCSRepo):

    branch = attr.ib(default=None)
    hexsha = attr.ib(default=None)
    describe = attr.ib(default=None)
    tracked_remote = attr.ib(default=None)
    remotes = attr.ib(default=attr.Factory(list))

# Probably generation wouldn't be flexible enough
#GitDistribution = get_vcs_distribution(GitRepo, 'git', 'Git')
@attr.s
class GitDistribution(VCSDistribution):
    _cmd = "git"
    packages = TypedList(GitRepo)

    def install_packages(self, session, use_version=True):
        raise NotImplementedError
GitRepo._distribution = GitDistribution


class SVNRepo(VCSRepo):

    revision = attr.ib(default=None)
    url = attr.ib(default=None)
    root_url = attr.ib(default=None)
    relative_url = attr.ib(default=None)

#SVNDistribution = get_vcs_distribution(SVNRepo, 'svn', 'SVN')
@attr.s
class SVNDistribution(VCSDistribution):
    _cmd = "svn"
    packages = TypedList(SVNRepo)

    def install_packages(self, session, use_version=True):
        raise NotImplementedError
SVNRepo._distribution = SVNDistribution


#
# Tracer Shims
# We use unified VCSTracer but it needs per-VCS specific handling/
# VCS objects are not created to worry/carry the session information
# so we have per-VCS shim objects which would be tracer helpers
# 
class GitSVNRepoShim(object):
    _ls_files_command = None  # just need to define in subclass
    _ls_files_filter = None
    
    _vcs_class = None  # associated VCS class

    def __init__(self, path, session):
        """Representation for a repository

        Parameters
        ----------
        path: str
           Path to the top of the repository

        """
        self.path = path.rstrip(os.sep)  # TODO: might be done as some rg to attr.ib
        self._session = session
        self._all_files = None
        self._branch = None

    def _session_execute_command(self, cmd, **kwargs):
        """Run in the session but providing our self.path as the cwd"""
        if 'cwd' not in kwargs:
            kwargs = dict(cwd=self.path, **kwargs)
        return self._session.execute_command(cmd, **kwargs)

    @property
    def all_files(self):
        """Lazy evaluation for _all_files. If session changes, result would be old"""
        if self._all_files is None:
            out, err = self._session_execute_command(self._ls_files_command)
            assert not err
            self._all_files = set(filter(None, out.split('\n')))
            if self._ls_files_filter:
                self._all_files = self._ls_files_filter(self._all_files)
            self._all_files = set(self._all_files)  # for efficient lookups
        return self._all_files

    def owns_path(self, path):
        # does this repository have this directory under its control?
        if path.rstrip(os.sep) == self.path:
            return True
        # it might be that the path points to itself
        # NOTE:
        #  this is an interesting case -- don't we want to still track "possible"
        #  artifacts produced from the repos?  e.g. ./build subdirectory
        #  But for that we would need to ask twice -- first a full sweep across
        #  all Resolvers making it all strict checks, and then again through
        #  those which could potentially claim it to belong to the repo?
        #  For now just a strict check, and we would want to request all files
        #  which repo knows about
        rpath = path[len(self.path)+1:]
        return rpath in self.all_files

    @classmethod
    def get_at_dirpath(cls, session, dirpath):
        """Return VCS instance at the given path (if under that VCS control)"""
        raise NotImplementedError



# Name must be   TYPERepo since used later in the code
# As an overkill might want some metaclass to look after that ;-)
class SVNRepoShim(GitSVNRepoShim):
    
    _vcs_class = SVNRepo
    _vcs_distribution_class = SVNDistribution
    
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
        super(SVNRepoShim, self).__init__(*args, **kwargs)
        self.__info = None

    @classmethod
    def get_at_dirpath(cls, session, dirpath):
        # ho ho -- no longer the case that there is .svn in each subfolder:
        # http://stackoverflow.com/a/9070242
        found = False
        if exists(opj(dirpath, '.svn')):  # early detection
            found = True
        # but still might be under SVN
        if not found:
            try:
                out, err = session.execute_command(
                    'svn info',
                    # expect_fail=True,
                    cwd=dirpath
                )
            except CommandError as exc:
                if "Please see the 'svn upgrade' command" in str(exc):
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
        return cls(dirpath, session=session)

    @property
    def _info(self):
        if self.__info is None:
            # TODO -- outdated repos might need 'svn upgrade' first
            # so not sure -- if we should copy them somewhere first and run
            # update there or ask user to update them on his behalf?!
            out, err = self._session.execute_command('svn info')
            self.__info = dict(
                [x.lstrip() for x in l.split(':', 1)]
                for l in out.splitlines() if l.strip()
            )
        return self.__info

    @property
    def revision(self):
        return self._info['Revision']

    @property
    def url(self):
        # also has similarity to APT in that we could have the top of SVN repo
        # as an 'origin' which might be reused by multiple 'sub-repos'/directories
        # "Repository Root" and "Relative URL"
        return self._info['URL']

    @property
    def root_url(self):
        return self._info['Repository Root']

    @property
    def relative_url(self):
        return self._info['Relative URL']

    @property
    def uuid(self):
        return self._info['Repository UUID']


class GitRepoShim(GitSVNRepoShim):

    _ls_files_command = 'git ls-files'

    _vcs_class = GitRepo
    _vcs_distribution_class = GitDistribution

    @classmethod
    def get_at_dirpath(cls, session, dirpath):
        try:
            out, err = session.execute_command(
                'git rev-parse --show-toplevel',
                # expect_fail=True,
                cwd=dirpath
            )
        except CommandError as exc:
            lgr.debug(
                "Probably %s is not under git repo path: %s",
                dirpath, exc_str(exc)
            )
            return None
        topdir = out.rstrip('\n')
        lgr.debug("Detected Git repository at %s for %s. Creating a session shim", topdir, dirpath)
        return cls(topdir, session=session)

    def _run_git(self, cmd, expect_fail=False, **kwargs):
        """Helper to run git command, and ignore stderr"""
        cmd = ['git'] + cmd if isinstance(cmd, list) else 'git ' + cmd
        try:
            out, err = self._session.execute_command(
                cmd,
                #expect_fail=expect_fail,
                **kwargs)
        except CommandError:
            if not expect_fail:
                raise
            else:
                return None
        return out.strip()

    @property
    def hexsha(self):
        try:
            return self._run_git('rev-parse HEAD')
        except CommandError:
            # might still be the first yet to be committed state in the branch
            return None
        
    @property
    def describe(self):
        """Let's use git describe"""
        try:
            return self._run_git('describe --tags') #, expect_fail=True)
        except CommandError:
            return None

    @property
    def remotes(self):
        # ideally needs to figure out the remote(s) which already have
        # this commit.  So kinda similar to APT where we list all origins
        # where some might not even contain current version. TODO: implement
        # that way
        #
        # On the other hand, I think it would not be uncommon to use some
        # version which is not yet pushed... so what additional information
        # would this check provide us?  We better record current branch,
        # and mark remote which is tracked for it
        hexsha = self.hexsha
        # which remotes contain this commit, so we could provide this
        # possibly valuable information
        if not hexsha:  # just initialized
            return []
        remote_branches = self._run_git(
            'branch -r --contains %s' % hexsha,
            expect_fail=True)
        if not remote_branches:
            return []
        containing_remotes = set(x.split('/', 1)[0] for x in remote_branches)
        remotes = {}
        for remote in self._run_git('remote').splitlines():
            rec = {}
            for f in 'url', 'pushurl':
                try:
                    rec[f] = self._run_git('config remote.%s.%s' % (remote, f)
                                           #, expect_fail=True,
                                           #, expect_stderr=True
                                           )
                except CommandError:
                    # must have no value
                    pass
            if remote in containing_remotes:
                rec['contains'] = True
            remotes[remote] = rec
        return remotes

    @property
    def tracked_remote(self):
        branch = self.branch
        if not branch:
            return None
        return self._run_git(
                'config branch.%s.remote' % (branch,)
                #, expect_stderr=True
                #, expect_fail=True
        ) or None         # want explicit None

    @property
    def branch(self):
        if self._branch is None:
            try:
                branch = self._run_git('rev-parse --abbrev-ref HEAD')
            except CommandError:
                # could yet happen there is no commit here, so branch is not defined?
                return None
            if branch != 'HEAD':
                self._branch = branch
        return self._branch


class VCSTracer(DistributionTracer):
    """Resolve files into VCS repositories they are contained with

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

    SHIMS = (SVNRepoShim, GitRepoShim)

    def _init(self):
        # dictionary to contain per each inspected/known directory a VCS
        # instance it belongs to
        self._known_repos = {}
        
    def identify_distributions(self, files):
        repos, remaining_files = self.identify_packages_from_files(files)
        pkgs_per_distr = defaultdict(list)
        for repo in repos:
            pkgs_per_distr[repo._distribution].append(repo)
        for dist_class, repos in pkgs_per_distr.items():
            yield dist_class(name=dist_class._cmd,
                             packages=repos), remaining_files

    def _get_packagefields_for_files(self, files):
        out = {}
        for f in files:
            shim = self._resolve_file(f)
            if not shim:
                continue
            # we probably do not want all the attributes to just report which
            # repo it is, so let's report path and type
            # out[f] = dict(
            #     (a.name, getattr(shim, a.name)) for a in shim._vcs_class.__attrs_attrs__
            #     if a.name not in {'files'}
            # )
            out[f] = {
                'path': shim.path,
                # 'repo_class': shim._vcs_class,
            }
            # the rest of the attrs will be taken by using _known_repos
            # in _create_package
        return out

    def _create_package(self, path):
        # TODO:  we might want to mark those which are found to belong to pkg
        #  files which are dirty.
        shim = self._known_repos[path]
        attrs = dict(
            (a.name, getattr(shim, a.name)) for a in shim._vcs_class.__attrs_attrs__
            if a.name not in {'files'}  # those will be populated later
        )
        attrs = only_with_values(attrs)
        return instantiate_attr_object(shim._vcs_class, attrs)

    def _resolve_file(self, path):
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
            if repo.owns_path(path):
                return repo

        # ok -- if it is not among known repos, we need to 'sniff' around
        # if there is a repository at that path
        for Shim in self.SHIMS:
            lgr.log(5, "Trying %s for path %s", Shim, path)
            shim = Shim.get_at_dirpath(self._session, dirpath) \
                if lexists(dirpath) else None
            if shim:
                # so there is one nearby -- record it
                self._known_repos[shim.path] = shim
                # but it might still not to know about the file
                if shim.owns_path(path):
                    return shim
                # if not -- just keep going to the next candidate repository
        return None
