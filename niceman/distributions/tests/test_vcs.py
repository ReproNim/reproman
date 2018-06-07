# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import os

import attr

from niceman.cmd import Runner
from niceman.distributions.vcs import VCSTracer
from niceman.utils import chpwd
from niceman.tests.utils import assert_is_subset_recur
from niceman.tests.fixtures import git_repo_fixture, svn_repo_fixture


git_repo_empty = git_repo_fixture(kind="empty")
git_repo = git_repo_fixture()
git_repo_pair = git_repo_fixture(kind="pair")

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
            expected_subset={"name": "git",
                             "packages": [{"files": paths,
                                           "path": git_repo,
                                           "branch": "master"}]})

        assert dists[0][0].packages[0].hexsha
        assert dists[0][0].packages[0].root_hexsha

        runner = Runner()
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
    runner = Runner()
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
    runner = Runner()
    tracer = VCSTracer()

    # Set remote.pushdefault to a value we know doesn't exist.
    # Otherwise, the test machine may have remote.pushdefault globally
    # configured to point to "origin".
    runner.run(["git", "config", "remote.pushdefault", "notexisting"],
               cwd=repo_local)
    # Add another remote that doesn't contain the current commit (in
    # fact doesn't actually exist), so that we test the "listed as
    # remote but doesn't contain" case.
    runner.run(["git", "remote", "add", "fakeremote", "fakepath"],
               cwd=repo_local)

    paths = [os.path.join(repo_local, "foo")]

    dists_nopush = list(tracer.identify_distributions(paths))
    assert_distributions(
        dists_nopush,
        expected_length=1,
        expected_subset={"name": "git",
                         "packages": [{"files": paths,
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
    runner.run(["git", "config", "remote.origin.pushurl", repo_remote],
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
