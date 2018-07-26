# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import os
import os.path as op

import attr
import copy
import logging
import pytest

from niceman.cmd import GitRunner
from niceman.distributions.vcs import VCSTracer
from niceman.support.exceptions import CommandError
from niceman.utils import chpwd
from niceman.utils import swallow_logs
from niceman.tests.utils import assert_is_subset_recur
from niceman.tests.utils import create_tree
from niceman.tests.utils import with_tree
from niceman.tests.fixtures import git_repo_fixture, svn_repo_fixture
from niceman.distributions.vcs import GitDistribution
from niceman.distributions.vcs import GitRepo

git_repo_empty = git_repo_fixture(kind="empty")
git_repo = git_repo_fixture()
git_repo_pair = git_repo_fixture(kind="pair")
git_repo_pair_module = git_repo_fixture(kind="pair", scope="module")

svn_repo_empty = svn_repo_fixture(kind='empty')
svn_repo = svn_repo_fixture()


# TODO: Move to niceman.test.utils and use in other tracer tests.
def assert_distributions(result, expected_length=None, which=0,
                         expected_unknown=None, expected_subset=None):
    """Wrap common assertions about identified distributions.

    Parameters
    ----------
    result : iterable
        The result of a tracer's identify_distributions method (in its
        original generator form or as a list).
    expected_length : int, optional
        Expected number of items in `result`.
    which : int, optional
        Index specifying which distribution from result to consider
        for the `expected_unknown` and `expected_subset`
        assertions.
    expected_unknown : list, optional
        Which files should be marked as unknown in distribution
        `which`.
    expected_subset : dict, optional
        This dict is expected to be a subset of the distribution
        `which`.  The check is done by `assert_is_subset_recur`.
    """
    result = list(result)

    if expected_length is not None:
        assert len(result) == expected_length

    dist, unknown_files = result[which]

    if expected_unknown is not None:
        assert unknown_files == expected_unknown

    if expected_subset is not None:
        assert_is_subset_recur(expected_subset, attr.asdict(dist), [dict, list])


def test_git_repo_empty(git_repo_empty):
    tracer = VCSTracer()
    # Should not crash when given path to empty repo.
    assert_distributions(
        tracer.identify_distributions([git_repo_empty]),
        expected_length=1,
        expected_unknown=set(),
        expected_subset={"name": "git",
                         "packages": [{"path": git_repo_empty,
                                       "branch": "master",
                                       # We do not include repo path itself.
                                       "files": []}]})


def test_git_repo(git_repo):
    paths = [
        # Both full ...
        os.path.join(git_repo, "foo"),
        # ... and relative paths work.
        "bar",
        # So do paths in subdirectories.
        os.path.join(git_repo, "subdir/baz")
    ]

    tracer = VCSTracer()

    with chpwd(git_repo):
        dists = list(tracer.identify_distributions(paths + ["/sbin/iptables"]))
        assert_distributions(
            dists,
            expected_length=1,
            expected_unknown={"/sbin/iptables"},
            expected_subset={
                "name": "git",
                "packages": [{"files": [op.relpath(p) for p in paths],
                              "path": git_repo,
                              "branch": "master"}]})

        assert dists[0][0].packages[0].hexsha
        assert dists[0][0].packages[0].root_hexsha

        runner = GitRunner()
        hexshas, _ = runner(["git", "rev-list", "master"], cwd=git_repo)
        root_hexsha = hexshas.strip('\n').split('\n')[-1]
        repo = dists[0][0].packages[0]
        assert repo.root_hexsha == root_hexsha
        assert repo.identifier == repo.root_hexsha
        assert repo.commit == repo.hexsha

        # Above we identify a subdirectory file, but we should not
        # identify the subdirectory itself because in principle Git is
        # not tracking directories.
        subdir = os.path.join(git_repo, "subdir")
        assert not list(tracer.identify_distributions([subdir]))


def test_git_repo_detached(git_repo):
    runner = GitRunner()
    # If we are in a detached state, we still don't identify the
    # repository itself.
    runner(["git", "checkout", "master^{}", "--"],
           cwd=git_repo, expect_stderr=True)

    hexsha_master, _ = runner(["git", "rev-parse", "master"],
                              cwd=git_repo)
    hexsha_master = hexsha_master.strip()

    tracer = VCSTracer()
    dists = list(tracer.identify_distributions([git_repo]))

    pkg = dists[0][0].packages[0]
    # We do not include repository path itself.
    assert pkg.files == []
    assert pkg.hexsha == hexsha_master
    assert not pkg.branch
    assert not pkg.remotes


def test_git_repo_remotes(git_repo_pair):
    repo_local, repo_remote = git_repo_pair
    runner = GitRunner()
    tracer = VCSTracer()

    # Set remote.pushdefault to a value we know doesn't exist.
    # Otherwise, the test machine may have remote.pushdefault globally
    # configured to point to "origin".
    runner(["git", "config", "remote.pushdefault", "notexisting"],
           cwd=repo_local)
    # Add another remote that doesn't contain the current commit (in
    # fact doesn't actually exist), so that we test the "listed as
    # remote but doesn't contain" case.
    runner(["git", "remote", "add", "fakeremote", "fakepath"],
           cwd=repo_local)

    paths = [os.path.join(repo_local, "foo")]

    dists_nopush = list(tracer.identify_distributions(paths))
    assert_distributions(
        dists_nopush,
        expected_length=1,
        expected_subset={
            "name": "git",
            "packages": [
                {"files": [op.relpath(p, repo_local) for p in paths],
                 "path": repo_local,
                 "branch": "master",
                 "tracked_remote": "origin",
                 "remotes": {"origin":
                             {"url": repo_remote,
                              "contains": True},
                             "fakeremote":
                             {"url": "fakepath"}}}]})
    pkg_nopush = dists_nopush[0][0].packages[0]
    assert set(pkg_nopush.remotes.keys()) == {"origin", "fakeremote"}

    # fakeremote, which doesn't contain the current commit, doesn't
    # have contains=True.
    assert "contains" in pkg_nopush.remotes["origin"]
    assert "contains" not in pkg_nopush.remotes["fakeremote"]
    # pushurl is not included in the output above because it is not
    # set.
    assert "pushurl" not in list(pkg_nopush.remotes.values())

    # If we set the pushurl and retrace, it is included.
    runner(["git", "config", "remote.origin.pushurl", repo_remote],
           cwd=repo_local)
    dists_push = list(tracer.identify_distributions(paths))
    pkg_push = dists_push[0][0].packages[0]
    assert pkg_push.remotes["origin"]["pushurl"] == repo_remote

    # If we are at a commit that none of the remotes are known to
    # contain, there are no listed remotes.
    with chpwd(repo_local):
        runner(["git", "commit", "--allow-empty", "-m", "empty commit"])

    dists_nocontain = list(tracer.identify_distributions(paths))
    assert not dists_nocontain[0][0].packages[0].remotes.values()

    # The remote repository, however, doesn't have a remote, so there
    # are not listed remotes.
    paths = [os.path.join(repo_remote, "foo")]
    dists_remote = list(tracer.identify_distributions(paths))
    assert not dists_remote[0][0].packages[0].remotes.values()


def test_git_install_no_remote():
    dist = GitDistribution(name="git",
                           packages=[GitRepo(path="/tmp/shouldnt/matter")])

    with swallow_logs(new_level=logging.WARNING) as log:
        dist.initiate()
        dist.install_packages()
        assert "No remote known" in log.out


@with_tree(tree={"foo": ""})
def test_git_install_skip_existing_nongit(path=None):
    with swallow_logs(new_level=logging.WARNING) as log:
        dist_dir = GitDistribution(
            name="git",
            packages=[
                GitRepo(path=path,
                        remotes={"origin": {"url": "doesnt-matter",
                                            "contains": True}})])
        dist_dir.install_packages()
        assert "not a Git repository; skipping" in log.out

    with swallow_logs(new_level=logging.WARNING) as log:
        dist_dir = GitDistribution(
            name="git",
            packages=[
                GitRepo(path=op.join(path, "foo"),
                        remotes={"origin": {"url": "doesnt-matter",
                                            "contains": True}})])
        dist_dir.install_packages()
        assert "not a directory; skipping" in log.out


def test_git_install_skip_different_git(git_repo):
    with swallow_logs(new_level=logging.WARNING) as log:
        dist_dir = GitDistribution(
            name="git",
            packages=[
                GitRepo(path=git_repo,
                        root_hexsha="definitely doesn't match",
                        remotes={"origin": {"url": "doesnt-matter",
                                            "contains": True}})])
        dist_dir.install_packages()
        assert "doesn't match expected hexsha; skipping" in log.out


@pytest.fixture(scope="module")
def traced_repo(git_repo_pair_module):
    """Return a Git repo pair and the traced GitDistribution for the local repo.
    """
    repo_local, repo_remote = git_repo_pair_module

    runner = GitRunner(cwd=repo_local)
    runner(["git", "remote", "add", "dummy-remote", "nowhere"])

    tracer = VCSTracer()
    dists = list(tracer.identify_distributions([op.join(repo_local, "foo")]))
    git_dist = dists[0][0]
    assert len(git_dist.packages) == 1

    return {"repo_local": repo_local,
            "repo_remote": repo_remote,
            "git_dist": git_dist}


@pytest.fixture(scope="function")
def traced_repo_copy(traced_repo):
    return copy.deepcopy(traced_repo)


def install(git_dist, dest, check=False):
    """Helper to install GitDistribution `git_dist` to `dest`.

    If `check`, trace the installed repository and run a basic comparison in
    the GitRepo objects.
    """
    tracer = VCSTracer()
    git_dist.install_packages()

    if check:
        dists_installed = list(
            tracer.identify_distributions([op.join(dest, "foo")]))
        git_dist_installed = dists_installed[0][0]
        assert len(git_dist_installed.packages) == 1
        git_pkg = git_dist.packages[0]
        git_pkg_installed = git_dist_installed.packages[0]

        for att in ["hexsha", "root_hexsha", "tracked_remote", "remotes"]:
            assert getattr(git_pkg, att) == getattr(git_pkg_installed, att)


def current_hexsha(runner):
    return runner(["git", "rev-parse", "HEAD"])[0].strip()


def current_branch(runner):
    try:
        out = runner(["git", "symbolic-ref", "--short", "HEAD"],
                     expect_fail=True)
    except CommandError:
        return
    return out[0].strip()


@pytest.mark.integration
def test_git_install(traced_repo_copy, tmpdir):
    git_dist = traced_repo_copy["git_dist"]
    git_pkg = git_dist.packages[0]
    tmpdir = str(tmpdir)

    # Install package to a new location.
    install_dir = op.join(tmpdir, "installed")
    git_pkg.path = install_dir

    install(git_dist, install_dir, check=True)
    # Installing a second time works if the root hexsha's match.
    install(git_dist, install_dir, check=True)

    runner = GitRunner(cwd=install_dir)

    # We don't try to change the state of the repository if it's dirty.
    runner(["git", "reset", "--hard", "HEAD^"])
    hexsha_existing = current_hexsha(runner)
    create_tree(install_dir, {"dirt": "dirt"})
    with swallow_logs(new_level=logging.WARNING) as log:
        install(git_dist, install_dir)
        assert "repository is dirty" in log.out
    assert current_hexsha(runner) == hexsha_existing

    # We end up on the intended commit (detached) if the existing installation
    # repo is clean.
    os.remove(op.join(install_dir, "dirt"))
    install(git_dist, install_dir)
    assert current_hexsha(runner) == git_pkg.hexsha
    assert not current_branch(runner)


@pytest.mark.integration
def test_git_install_detached(traced_repo_copy, tmpdir):
    git_dist = traced_repo_copy["git_dist"]
    git_pkg = git_dist.packages[0]
    tmpdir = str(tmpdir)

    # Install package to a new location.
    install_dir = op.join(tmpdir, "installed")
    git_pkg.path = install_dir
    runner = GitRunner(cwd=install_dir)
    install(git_dist, install_dir)

    # We detach if there is no recorded branch.
    git_pkg.branch = None
    runner(["git", "checkout", "master"])
    install(git_dist, install_dir)
    assert current_hexsha(runner) == git_pkg.hexsha
    assert not current_branch(runner)


@pytest.mark.integration
def test_git_install_hexsha_not_found(traced_repo_copy, tmpdir):
    git_dist = traced_repo_copy["git_dist"]
    git_pkg = git_dist.packages[0]
    tmpdir = str(tmpdir)

    # Install package to a new location.
    install_dir = op.join(tmpdir, "installed")
    git_pkg.path = install_dir
    install(git_dist, install_dir)

    # No existing hexsha.
    git_pkg.hexsha = "0" * 40
    with swallow_logs(new_level=logging.WARNING) as log:
        install(git_dist, install_dir)
        assert "expected hexsha wasn't found" in log.out


@pytest.mark.integration
def test_git_install_checkout(traced_repo_copy, tmpdir):
    git_dist = traced_repo_copy["git_dist"]
    git_pkg = git_dist.packages[0]
    tmpdir = str(tmpdir)

    install_dir = op.join(tmpdir, "installed")
    runner = GitRunner(cwd=install_dir)

    # Installing to a non-existing location will be more aggressive, creating a
    # new branch at the recorded hexsha rather than just detaching there.
    git_pkg.path = install_dir
    git_pkg.branch = "other"
    install(git_dist, install_dir, check=True)
    assert current_branch(runner) == "other"

    # If the recorded branch is in the existing installation repo and has the
    # same hexsha, we check it out.
    runner(["git", "checkout", "master"])
    runner(["git", "branch", "--force", "other", git_pkg.hexsha])
    install(git_dist, install_dir)
    assert current_hexsha(runner) == git_pkg.hexsha
    assert current_branch(runner) == "other"
    # Otherwise, we detach.
    runner(["git", "checkout", "master"])
    runner(["git", "branch", "--force", "other", git_pkg.hexsha + "^"])
    install(git_dist, install_dir)
    assert current_hexsha(runner) == git_pkg.hexsha
    assert not current_branch(runner)


@pytest.mark.integration
def test_git_install_add_remotes(traced_repo_copy, tmpdir):
    git_dist = traced_repo_copy["git_dist"]
    git_pkg = git_dist.packages[0]
    tmpdir = str(tmpdir)

    install_dir = op.join(tmpdir, "installed")
    runner = GitRunner(cwd=install_dir)

    git_pkg.path = install_dir
    git_pkg.tracked_remote = "foo"
    url = git_pkg.remotes["origin"]["url"]
    git_pkg.remotes = {"foo": {"url": url},
                       "bar": {"contains": True, "url": url}}
    install(git_dist, install_dir)
    installed_remotes = runner(["git", "remote"],
                               cwd=install_dir)[0].splitlines()
    assert set(installed_remotes) == {"foo", "bar"}


def test_svn(svn_repo):
    (svn_repo_root, checked_out_dir) = svn_repo
    svn_file = os.path.join(checked_out_dir, 'foo')
    uuid_file = os.path.join(svn_repo_root, 'db', 'uuid')
    uuid = open(uuid_file).readlines()[0].strip()
    tracer = VCSTracer()
    assert_distributions(
        tracer.identify_distributions([svn_file]),
        expected_length=1,
        expected_subset={'name': 'svn'})
    svn_repo = list(tracer.identify_distributions([svn_file]))[0][0].packages[0]
    assert svn_repo.files == ['foo']
    assert svn_repo.uuid == uuid
    assert svn_repo.root_url == 'file://' + svn_repo_root
    assert svn_repo.revision == 1
    assert svn_repo.identifier == svn_repo.uuid
    assert svn_repo.commit == svn_repo.revision


def test_empty_svn(svn_repo_empty):
    (svn_repo_root, checked_out_dir) = svn_repo_empty
    tracer = VCSTracer()
    distributions = list(tracer.identify_distributions([checked_out_dir]))
    svn_repo = distributions[0][0].packages[0]
    assert svn_repo.revision is None
