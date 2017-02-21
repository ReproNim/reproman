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

from os.path import dirname, isdir, isabs
from os.path import exists, lexists
from os.path import join as opj

from logging import getLogger
from six import viewvalues

from niceman.dochelpers import exc_str

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

    def __init__(self, path):
        """Representation for Git or SVN repository

        Parameters
        ----------
        path: str
           Path to the top of the repository

        """
        super(GitSVNRepo, self).__init__(self, path)
        self._files = None

    @property
    def files(self):
        if self._files is None:
            out, err = Runner(env={'LC_ALL': 'C'}, cwd=self.path)(
                self._ls_files_command
            )
            assert not err
            self._files = set(filter(None, out.split('\n')))
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


class SVNRepo(GitSVNRepo):
    _ls_files_command = 'sqlite3 -batch .svn/wc.db ".headers off" "select local_relpath from nodes_base"'

    @classmethod
    def get_at_dirpath(cls, dirpath):
        if not exists(opj(dirpath, '.svn')):
            return None
        # for now we treat each directory under SVN independently
        # pros:
        #   - could provide us 'minimal' set of checkouts to do, since it might be
        #      quite expensive to checkout the entire tree if it was not used
        #      besides few leaves
        lgr.debug("Detected SVN repository at %s", dirpath)
        return cls(dirpath)


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


    def _create_package(self, pkgname):
        raise NotImplementedError


    def _get_packages_for_files(self, files):
        file_to_package_dict = {}

        return file_to_package_dict

    def resolve_file(self, path):
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
            if os.path.commonprefix(repo.path, path) != repo.path:
                continue

            # could be less efficient than some str manipulations but ok for now
            # since we rely on a strict check (must be registered within the repo)
            if repo.is_mine(path):
                return repo

        # ok -- if it is not among known repos, we need to 'sniff' around
        # if there is a repository at that path
        for VCS in self.REGISTERED_VCS:
            vcs = VCS.get_at_dirpath(dirpath)
            if vcs:
                # so there is one nearby -- record it
                self._known_repos[vcs.path] = vcs
                # but it might still not to know about the file
                if vcs.is_mine(path):
                    return vcs
                # if not -- just keep going to the next candidate repository
        return None


    # actually we might better just overload the entire search
    def search_for_files(self, files):
        """Identifies the VCS repos for a given collection of files


        Parameters
        ----------
        files : iterable
            Container (e.g. list or set) of file paths

        Return
        ------
        (found_packages, unknown_files)
            - found_packages is an array of dicts that holds information about
              the found packages. Package dicts need at least "name" and
              "files" (that contains an array of related files)
            - unknown_files is a list of files that were not found in
              a package
        """
        unknown_files = set()
        found_packages = {}  # TODO: rename?
        nb_pkg_files = 0

        file_to_package_dict
        for f in files:
            # Stores the file
            if f not in file_to_package_dict:
                unknown_files.add(f)
            else:
                pkgname = file_to_package_dict[f]
                if pkgname in found_packages:
                    found_packages[pkgname]["files"].append(f)
                    nb_pkg_files += 1
                else:
                    pkg = self._create_package(pkgname)
                    if pkg:
                        found_packages[pkgname] = pkg
                        pkg["files"].append(f)
                        nb_pkg_files += 1
                    else:
                        unknown_files.add(f)

        # here we need also to get "leaf" vcs possibly sitting on top of
        # unknown files since later those might be used to hint to produced
        # artifacts.  They will have no files associated with them
        # TODO

        lgr.info("%d packages with %d files, and %d other files",
                 len(found_packages),
                 nb_pkg_files,
                 len(unknown_files))

        return list(viewvalues(found_packages)), unknown_files

    def identify_package_origins(self, *args, **kwargs):
        # no origins for any VCS AFAIK
        return None
