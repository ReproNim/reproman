# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrators for `reproman run`.

This module has three main parts:

 (1) The Orchestrator and DataladOrchestrator base classes define the
     interface. The two most important methods these leave undefined are
     prepare_remote() and fetch().

 (2) Mixin classes define prepare_remote() and fetch().

 (3) Concrete classes bring together 1 and (combinations of) 2.
"""

import abc
import collections
from contextlib import contextmanager
import logging
import os
import os.path as op
import uuid
from tempfile import NamedTemporaryFile
import time

from shlex import quote as shlex_quote

from reproman.dochelpers import borrowdoc
from reproman.utils import cached_property
from reproman.utils import chpwd
from reproman.utils import write_update
from reproman.resource.ssh import SSHSession
from reproman.support.jobs.submitters import SUBMITTERS
from reproman.support.jobs.template import Template
from reproman.support.exceptions import CommandError
from reproman.support.exceptions import MissingExternalDependency
from reproman.support.exceptions import OrchestratorError
from reproman.support.external_versions import external_versions

lgr = logging.getLogger("reproman.support.jobs.orchestrators")


# Abstract orchestrators


class Orchestrator(object, metaclass=abc.ABCMeta):
    """Base Orchestrator class.

    An Orchestrator is responsible for preparing a directory to run a command,
    submitting it with the specified submitter, and then handling the results.

    Parameters
    ----------
    resource : Resource instance
        Resource to run the command on.
    submission_type : str
        A key from `reproman.support.jobs.submitters.SUBMITTERS` that
        identifies which submitter should be used.
    job_spec : dict or None, optional
        These items control aspects of the run in several (too many) ways: (1)
        these items are exposed as keywords to the runscript and submit
        templates, (2) the orchestrator looks here for optional values like
        "working_directory" and "inputs", and (3) on resurrection, the
        orchestrator looks here for other required values, like "jobid".

        The details around the job_spec are somewhat loose and poorly defined
        at the moment.
    resurrection : boolean, optional
        Whether this instance represents a previous Orchestrator that already
        submitted a job. This allows a detached job to be fetched.
    """

    template_name = None

    def __init__(self, resource, submission_type, job_spec=None,
                 resurrection=False):
        self.resource = resource
        self.session = resource.get_session()
        self._resurrection = resurrection

        # TODO: Probe remote and try to infer.
        submitter_class = SUBMITTERS[submission_type or "local"]
        self.submitter = submitter_class(self.session)

        self.job_spec = job_spec or {}

        if resurrection:
            important_keys = ["jobid", "root_directory", "working_directory",
                              "local_directory"]
            for key in important_keys:
                if key not in self.job_spec:
                    raise OrchestratorError(
                        "Job spec must have key '{}' to resurrect orchestrator"
                        .format(key))

            self.jobid = self.job_spec["jobid"]
        else:
            self.jobid = "{}-{}".format(time.strftime("%Y%m%d-%H%M%S"),
                                        str(uuid.uuid4())[:4])
            self._prepare_spec()

        self.template = None

    def _find_root(self):
        home = self.session.query_envvars().get("HOME")
        if not home:
            raise OrchestratorError("Could not determine $HOME on remote")
        root_directory = op.join(home, ".reproman", "run-root")
        lgr.info("No root directory supplied for %s; using '%s'",
                 self.resource.name, root_directory)
        if not op.isabs(root_directory):
            raise OrchestratorError(
                "Root directory is not an absolute path: {}"
                .format(root_directory))
        return root_directory

    @property
    @cached_property
    def root_directory(self):
        """The root run directory on the resource.

        By default, the working directory for a particular command is a
        subdirectory of this directory. Orchestrators can also use this root to
        store things outside of the working directory (e.g. artifacts used in
        the fetch).
        """
        # TODO: We should allow root directory to be configured for each
        # resource.  What's the best way to do this?  Adding an attr for each
        # resource class is a lot of duplication.
        return self.job_spec.get("root_directory") or self._find_root()

    @abc.abstractproperty
    def working_directory(self):
        """Directory in which to run the command.
        """

    @property
    @cached_property
    def meta_directory(self):
        """Directory used to store metadata for the run.

        This directory must be a subdirectory of `working_directory`.
        """
        return op.join(self.working_directory, ".reproman", "jobs",
                       self.resource.name, self.jobid)

    @property
    @cached_property
    def local_directory(self):
        """Directory on local machine.
        """
        return self.job_spec.get("local_directory") or os.getcwd()

    def as_dict(self):
        """Represent Orchestrator as a dict.

        The information here will be used to re-initialize an equivalent object
        (e.g., if fetching results from a detached run).
        """
        # Items that may not be in `templates.kwds`.
        to_dump = {"resource_id": self.resource.id,
                   "resource_name": self.resource.name,
                   "local_directory": self.local_directory,
                   "orchestrator": self.name,
                   "submitter": self.submitter.name,
                   "submission_id": self.submitter.submission_id}
        return dict(to_dump, **(self.template.kwds if self.template else {}))

    def _prepare_spec(self):
        """Prepare the spec for the run.

        At the moment, this means the "inputs" and "outputs" keys in `spec` are
        replaced and the original are moved under the `*_unexpanded` key.
        """
        from reproman.support.globbedpaths import GlobbedPaths

        spec = self.job_spec
        for key in ["inputs", "outputs"]:
            if key in spec:
                spec["{}_unexpanded".format(key)] = spec[key]
                gp = GlobbedPaths(spec[key])
                spec["{}".format(key)] = gp.expand(dot=False)

        # Note: This doesn't adjust the command. We currently don't support any
        # datalad-run-like command formatting.

    @abc.abstractmethod
    def prepare_remote(self):
        """Prepare remote for run.
        """

    def _put_text(self, text, target, executable=False):
        """Put file with content `text` at `target`.

        Parameters
        ----------
        text : str
            Content for file.
        target : str
            Path on resource (passed as destination to `session.put`).
        executable : boolean, optional
            Whether to mark file as executable.
        """
        with NamedTemporaryFile('w', prefix="reproman-", delete=False) as tfh:
            tfh.write(text)
        if executable:
            os.chmod(tfh.name, 0o755)
        self.session.put(tfh.name, target)
        os.unlink(tfh.name)

    def submit(self):
        """Submit the job with `submitter`.
        """
        lgr.info("Submitting %s", self.jobid)
        templ = Template(
            **dict(self.job_spec,
                   jobid=self.jobid,
                   num_subjobs=1,
                   root_directory=self.root_directory,
                   working_directory=self.working_directory,
                   meta_directory=self.meta_directory,
                   meta_directory_rel=op.relpath(self.meta_directory,
                                                 self.working_directory)))
        self.template = templ
        self._put_text(
            templ.render_runscript("{}.template.sh".format(
                self.template_name or self.name)),
            op.join(self.meta_directory, "runscript"),
            executable=True)

        submission_file = op.join(self.meta_directory, "submit")
        self._put_text(
            templ.render_submission("{}.template".format(self.submitter.name)),
            submission_file,
            executable=True)

        subm_id = self.submitter.submit(
            submission_file,
            submit_command=self.job_spec.get("submit_command"))
        if subm_id is None:
            lgr.warning("No submission ID obtained for %s", self.jobid)
        else:
            lgr.info("Job %s submitted as %s job %s",
                     self.jobid, self.submitter.name, subm_id)
            self.session.execute_command("echo {} >{}".format(
                subm_id,
                op.join(self.meta_directory, "idmap")))

    def get_status(self, subjob=0):
        status_file = op.join(self.meta_directory,
                              "status.{:d}".format(subjob))
        status = "unknown"
        if self.session.exists(status_file):
            status = self.session.read(status_file).strip()
        return status

    @property
    def status(self):
        """Get information from job status file.
        """
        return self.get_status()

    @property
    def has_completed(self):
        """Has the run, including post-command processing, completed?
        """
        return self.session.exists(
            op.join(self.root_directory, "completed", self.jobid))

    @property
    def failed_subjobs(self):
        """List of failed subjobs (represented by index, starting with 0).
        """
        failed_dir = op.join(self.meta_directory, "failed")
        try:
            stdout, _ = self.session.execute_command(["ls", failed_dir])
        except CommandError:
            if self.session.exists(failed_dir):
                # This shouldn't have failed.
                raise OrchestratorError(CommandError)
            return []
        return list(map(int, stdout.strip().split()))

    @staticmethod
    def _log_failed(jobid, metadir, failed):
        failed = list(sorted(failed))
        num_failed = len(failed)
        lgr.warning("%d subjob%s failed. Check files in %s",
                    num_failed,
                    "" if num_failed == 1 else "s",
                    metadir)

        if num_failed == 1:
            stderr_suffix = str(failed[0])
        elif num_failed > 6:
            # Arbitrary cut-off to avoid listing excessively long.
            stderr_suffix = "*"
        else:
            stderr_suffix = "{{{}}}".format(
                ",".join(str(i) for i in failed))
        lgr.info("%s stderr: %s",
                 jobid,
                 op.join(metadir, "stderr." + stderr_suffix))

    def log_failed(self, func=None):
        """Display a log message about failed status.

        Parameters
        ----------
        func : callable or None, optional
            If a failed status is detected, call this function with two
            arguments, the local metadata directory and a list of failed
            subjobs.
        """
        failed = self.failed_subjobs
        if failed:
            local_metadir = op.join(
                self.local_directory,
                op.relpath(op.join(self.meta_directory),
                           self.working_directory),
                "")
            self._log_failed(self.jobid, local_metadir, failed)
            if func:
                func(local_metadir, failed)

    def follow(self):
        """Follow command, exiting when post-command processing completes."""
        self.submitter.follow()
        # We're done according to the submitter. This includes the
        # post-processing. Make sure it looks like it passed.
        if not self.has_completed:
            raise OrchestratorError(
                "Post-processing failed for {} [status: {}] ({})"
                .format(self.jobid, self.status, self.working_directory))

    def _get_io_set(self, which):
        spec = self.job_spec
        return {fname for fname in spec.get(which, [])}

    def get_inputs(self):
        """Return input files.

        Returns
        -------
        Set of str
        """
        return self._get_io_set("inputs").union(
            self._get_io_set("extra_inputs"))

    def get_outputs(self):
        """Return output files.

        Returns
        -------
        Set of str
        """
        return self._get_io_set("outputs")

    @abc.abstractmethod
    def fetch(self):
        """Fetch the submission result.

        In addition to doing whatever is need to fetch the results, this method
        should call `self.log_failed` at the end.
        """


def _datalad_check_container(ds, spec):
    """Adjust spec for `datalad-container`-configured container.

    If a "container" key is found, "command_str" will be replaced, and the
    previous "command_str" value will be placed under
    "command_str_nocontainer".
    """
    container = spec.get("container")
    if container is not None:
        external_versions.check("datalad_container", min_version="0.4.0")
        from datalad_container.find_container import find_container
        try:
            cinfo = find_container(ds, container)
        except ValueError as exc:
            raise OrchestratorError(exc)

        cmdexec = cinfo["cmdexec"]
        image = op.relpath(cinfo["path"], ds.path)

        command_str = spec["command_str"]
        spec["commmand_str_nocontainer"] = command_str
        spec["command_str"] = cmdexec.format(img=image, cmd=command_str)
        spec["extra_inputs"] = [image]


def _datalad_format_command(ds, spec):
    """Adjust `spec` to use `datalad run`-style formatting.

    The "inputs", "outputs", and "command_str" keys in `spec` are replaced and
    the original are moved under the `*_unexpanded` key.
    """
    from datalad.interface.run import format_command
    # DataLad's GlobbedPaths _should_ be the same as ours, but let's use
    # DataLad's to avoid potential discrepancies with datalad-run's behavior.
    from datalad.interface.run import GlobbedPaths

    fmt_kwds = {}
    for key in ["inputs", "outputs"]:
        if key in spec:
            spec["{}_unexpanded".format(key)] = spec[key]
            gp = GlobbedPaths(spec[key])
            spec[key] = gp.expand(dot=False)
            fmt_kwds[key] = gp

    cmd_expanded = format_command(ds, spec["command_str"], **fmt_kwds)
    spec["command_str_unexpanded"] = spec["command_str"]
    spec["command_str"] = cmd_expanded


class DataladOrchestrator(Orchestrator, metaclass=abc.ABCMeta):
    """Execute command assuming (at least) a local dataset.
    """

    def __init__(self, resource, submission_type, job_spec=None,
                 resurrection=False):
        if not external_versions["datalad"]:
            raise MissingExternalDependency(
                "DataLad is required for orchestrator '{}'".format(self.name))

        super(DataladOrchestrator, self).__init__(
            resource, submission_type, job_spec, resurrection=resurrection)

        from datalad.api import Dataset
        self.ds = Dataset(".")
        if not self.ds.id:
            raise OrchestratorError("orchestrator {} requires a local dataset"
                                    .format(self.name))

        if self._resurrection:
            self.head = self.job_spec.get("head")
        else:
            self._configure_repo()
            self.head = self.ds.repo.get_hexsha()
            _datalad_check_container(self.ds, self.job_spec)
            _datalad_format_command(self.ds, self.job_spec)

    @property
    @cached_property
    @borrowdoc(Orchestrator)
    def working_directory(self):
        wdir = self.job_spec.get("working_directory")
        return wdir or op.join(self.root_directory, self.ds.id)

    @property
    @borrowdoc(Orchestrator)
    def local_directory(self):
        return self.ds.path

    @property
    @cached_property
    def job_refname(self):
        return "refs/reproman/{}".format(self.jobid)

    @borrowdoc(Orchestrator)
    def as_dict(self):
        d = super(DataladOrchestrator, self).as_dict()
        d["dataset_id"] = self.ds.id
        d["head"] = self.head
        return d

    def _prepare_spec(self):
        # Disable. _datalad_format_command() and _datalad_format_command()
        # handle this in __init__(). We can't just call those here because the
        # self.ds wouldn't be defined yet.
        pass

    def _configure_repo(self):
        gitignore = op.join(self.ds.path, ".reproman", "jobs", ".gitignore")
        write_update(
            gitignore,
            ("# Automatically created by ReproMan.\n"
             "# Do not change manually.\n"
             "log.*\n"))

        gitattrs = op.join(self.ds.path, ".reproman", "jobs", ".gitattributes")
        write_update(
            gitattrs,
            ("# Automatically created by ReproMan.\n"
             "# Do not change manually.\n"
             "status.[0-9]* annex.largefiles=nothing\n"
             "**/failed/* annex.largefiles=nothing\n"
             "idmap annex.largefiles=nothing\n"))

        self.ds.add([gitignore, gitattrs],
                    message="[ReproMan] Configure jobs directory")


# Orchestrator method mixins


class PrepareRemotePlainMixin(object):

    def prepare_remote(self):
        """Prepare "plain" execution directory on remote.

        Create directory and copy inputs to it.
        """
        # TODO: Provide better handling of existing directories. This is
        # unlikely to happen with the default working directory but can easily
        # happen with user-supplied working directory.

        session = self.session
        if not session.exists(self.root_directory):
            session.mkdir(self.root_directory, parents=True)

        for i in self.get_inputs():
            session.put(i, op.join(self.working_directory,
                                   op.relpath(i, self.local_directory)))


def _format_ssh_url(user, host, port, path):
    """Format an SSH URL for DataLad, considering installed version.
    """
    if external_versions["datalad"] >= "0.11.2":
        fmt = "ssh://{user}{host}{port}{path}"
        warn = False
    else:
        # Stick to git scp-like syntax because create-sibling will fail with
        # something like
        #
        #   stderr: 'fatal: ssh variant 'simple' does not support setting port'
        #   [cmd.py:wait:415] (GitCommandError)
        #
        # with the default value of ssh.variant. For non-standard ports, this
        # relies on the user setting up their ssh config.
        fmt = "{user}{host}:{path}"
        warn = port is not None
        port = None
    sshurl = fmt.format(user=user + "@" if user else "",
                        host=host,
                        port=":" + str(port) if port is not None else "",
                        path=path)

    if warn:
        lgr.warning("Using SSH url %s; "
                    "port should be specified in SSH config",
                    sshurl)
    return sshurl


class PrepareRemoteDataladMixin(object):

    def _execute_in_wdir(self, command, err_msg=None):
        """Helper to run command in remote working directory.

        TODO: Adjust (or perhaps remove entirely) once
        `SSHSession.execute_command` supports the `cwd` argument.

        Parameters
        ----------
        command : str
        err_msg : optional
            Message to use if an OrchestratorError is raised.

        Returns
        -------
        standard output

        Raises
        ------
        OrchestratorError if command fails.
        """
        prefix = "cd '{}' && ".format(self.working_directory)
        try:
            out, _ = self.session.execute_command(prefix + command)
        except CommandError as exc:
            raise OrchestratorError(
                str(exc) if err_msg is None else err_msg)
        return out

    @property
    def status(self):
        """Like Orchestrator.status, but inspect the job's git ref if needed.
        """
        status = super(DataladOrchestrator, self).status
        if status == "unknown":
            # The local tree might be different because of another just. Check
            # the ref for the status.
            status_from_ref = self._execute_in_wdir(
                "git cat-file -p {}:{}"
                .format(self.job_refname,
                        op.relpath(op.join(self.meta_directory, "status.0"),
                                   self.working_directory)))
            status = status_from_ref.strip() or status
        return status

    @property
    def failed_subjobs(self):
        """Like Orchestrator.failed_subjobs, but inspect the job's git ref if needed.
        """
        failed = super(DataladOrchestrator, self).failed_subjobs
        if not failed:
            meta_tree = "{}:{}".format(
                self.job_refname,
                op.relpath(self.meta_directory, self.working_directory))
            try:
                failed_ref = self._execute_in_wdir(
                    "git ls-tree {}".format(op.join(meta_tree, "failed")))
            except OrchestratorError as exc:
                # Most likely, there were no failed subjobs and the "failed"
                # tree just doesn't exist. Let's see if we can find the meta
                # directory, which should always be there.
                try:
                    self._execute_in_wdir("git ls-tree {}".format(meta_tree))
                except OrchestratorError:
                    # All right, something looks off.
                    raise exc
            else:
                failed = list(map(int, failed_ref.strip().split())) or failed
        return failed

    def _assert_clean_repo(self):
        if self._execute_in_wdir("git status --porcelain"):
            raise OrchestratorError("Remote repository {} is dirty"
                                    .format(self.working_directory))

    def _checkout_target(self):
        self._assert_clean_repo()
        target_commit = self.head
        self._execute_in_wdir(
            "git rev-parse --verify {}^{{commit}}".format(target_commit),
            err_msg=("Target commit wasn't found in remote repository {}"
                     .format(self.working_directory)))

        head_commit = self._execute_in_wdir(
            "git rev-parse HEAD",
            err_msg=("Could not find current commit in remote repository {}"
                     .format(self.working_directory)))

        if target_commit != head_commit.strip():
            lgr.info("Checking out %s in remote repository %s",
                     target_commit, self.working_directory)
            self._execute_in_wdir("git checkout {}".format(target_commit))

    def prepare_remote(self):
        """Prepare dataset sibling on remote.
        """
        if not self.ds.repo.get_active_branch():
            # publish() fails when HEAD is detached.
            raise OrchestratorError(
                "You must be on a branch to use the {} orchestrator"
                .format(self.name))
        if not self.session.exists(self.root_directory):
            self.session.mkdir(self.root_directory, parents=True)

        resource = self.resource
        session = self.session

        inputs = list(self.get_inputs())
        if isinstance(session, SSHSession):
            if resource.key_filename:
                dl_version = external_versions["datalad"]
                if dl_version < "0.11.3":
                    # Connecting will probably fail because `key_filename` is
                    # set, but we have no way to tell DataLad about it.
                    lgr.warning(
                        "DataLad version %s detected. "
                        "0.11.3 or greater is required to use an "
                        "identity file not specified in ~/.ssh/config",
                        dl_version)
                # Make the identity file available to 'datalad sshrun' even if
                # it is not configured in .ssh/config. This is particularly
                # important for AWS keys.
                os.environ["DATALAD_SSH_IDENTITYFILE"] = resource.key_filename
                from datalad import cfg
                cfg.reload(force=True)

            sshurl = _format_ssh_url(
                resource.user,
                # AWS resource does not have host attribute.
                getattr(resource, "host", None) or session.connection.host,
                getattr(resource, "port", None),
                self.working_directory)

            # TODO: Add one level deeper with reckless clone per job to deal
            # with concurrent jobs?
            if not session.exists(self.working_directory):
                remotes = self.ds.repo.get_remotes()
                if resource.name in remotes:
                    raise OrchestratorError(
                        "Remote '{}' unexpectedly exists. "
                        "Either delete remote or rename resource."
                        .format(resource.name))

                self.ds.create_sibling(sshurl, name=resource.name,
                                       recursive=True)
                since = None  # Avoid since="" for non-existing repo.
            else:
                remote_branch = "{}/{}".format(
                    resource.name,
                    self.ds.repo.get_active_branch())
                if self.ds.repo.commit_exists(remote_branch):
                    since = ""
                else:
                    # If the remote branch doesn't exist yet, publish will fail
                    # with since="".
                    since = None

            from datalad.support.exceptions import IncompleteResultsError
            try:
                self.ds.publish(to=resource.name, since=since, recursive=True)
            except IncompleteResultsError:
                raise OrchestratorError(
                    "'datalad publish' failed. Try running "
                    "'datalad update -s {} --merge --recursive' first"
                    .format(resource.name))

            self._checkout_target()

            if inputs:
                lgr.info("Making inputs available")
                try:
                    # TODO: Whether we try this `get` should be configurable.
                    self._execute_in_wdir("datalad get {}".format(
                        # FIXME: This should use something like
                        # execute_command_batch.
                        " ".join(map(shlex_quote, inputs))))
                except OrchestratorError:
                    # Should use --since for existing repo, but it doesn't seem
                    # to sync wrt content.
                    self.ds.publish(to=resource.name, path=inputs,
                                    recursive=True)
        elif resource.type == "shell":
            import datalad.api as dl
            if not session.exists(self.working_directory):
                dl.install(self.working_directory, source=self.ds.path)

            self.session.execute_command(
                "git push '{}' HEAD:{}-base"
                .format(self.working_directory, self.job_refname))
            self._checkout_target()

            if inputs:
                installed_ds = dl.Dataset(self.working_directory)
                installed_ds.get(inputs)
        else:
            # TODO: Handle more types?
            raise OrchestratorError("Unsupported resource type {}"
                                    .format(resource.type))

        if not session.exists(self.meta_directory):
            session.mkdir(self.meta_directory, parents=True)


class FetchPlainMixin(object):

    def fetch(self):
        """Get outputs from remote.
        """
        for o in self.get_outputs():
            self.session.get(
                o if op.isabs(o) else op.join(self.working_directory, o),
                # Make sure directory has trailing slash so that get doesn't
                # treat it as the file.
                op.join(self.local_directory, ""))

        def get_failed_meta(mdir, failed):
            for idx in failed:
                for f in ["status", "stdout", "stderr"]:
                    self.session.get(
                        op.join(self.meta_directory,
                                "{}.{:d}".format(f, idx)),
                        op.join(self.local_directory,
                                op.relpath(self.meta_directory,
                                           self.working_directory),
                                ""))
        self.log_failed(get_failed_meta)


@contextmanager
def head_at(dataset, commit):
    """Run block with `commit` checked out in `dataset`.

    Check `commit` out if HEAD isn't already at it and restore the previous
    HEAD and branch on exit. Note: If `commit` is a ref, this function is
    concerned only with checking out the dereferenced commit.

    Parameters
    ----------
    dataset : DataLad dataset
    commit : str
        A commit-ish.

    Yields
    ------
    A boolean indicating whether HEAD needed to be moved in order to make
    `commit` current.
    """
    if dataset.repo.dirty:
        raise OrchestratorError(
            "Refusing to work with dirty repository: {}"
            .format(dataset.path))

    try:
        commit = dataset.repo.get_hexsha(commit)
    except ValueError:
        raise OrchestratorError("Could not resolve '{}' in {}"
                                .format(commit, dataset.path))
    current = dataset.repo.get_hexsha()
    if current is None:
        raise OrchestratorError("No commits on current branch in {}"
                                .format(dataset.path))
    to_restore = dataset.repo.get_active_branch() or current

    moved = commit != current
    if moved:
        lgr.info("Checking out %s", commit)
        try:
            dataset.repo.checkout(commit)
            yield moved
        finally:
            lgr.info("Restoring checkout of %s", to_restore)
            dataset.repo.checkout(to_restore)
    else:
        yield moved


class FetchDataladPairMixin(object):

    def fetch(self):
        """Fetch the results from the remote dataset sibling.
        """
        lgr.info("Fetching results for %s", self.jobid)
        if self.resource.type == "ssh":
            ref = self.job_refname
            self.ds.repo.fetch(self.resource.name, "{0}:{0}".format(ref))
            self.ds.update(sibling=self.resource.name,
                           merge=True, recursive=True)
            with head_at(self.ds, ref):
                outputs = list(self.get_outputs())
                if outputs:
                    self.ds.get(path=outputs)
            if not self.ds.repo.is_ancestor(ref, "HEAD"):
                lgr.info("Results stored on %s. "
                         "Bring them into this branch with "
                         "'git merge %s'",
                         ref, ref)
        elif self.resource.type == "shell":
            # Below is just for local testing.  It doesn't support actually
            # getting the content.
            with chpwd(self.ds.path):
                self.session.execute_command(
                    ["git", "fetch", self.working_directory,
                     "{0}:{0}".format(self.job_refname)])
                self.session.execute_command(
                    ["git", "merge", "FETCH_HEAD"])

        def get_metadir(mdir, _):
            if self.resource.type == "ssh":
                self.ds.get(path=mdir)

        self.log_failed(get_metadir)


class FetchDataladRunMixin(object):

    def fetch(self):
        """Fetch results tarball and inject run record into the local dataset.
        """
        lgr.info("Fetching results for %s", self.jobid)
        import tarfile
        tfile = "{}.tar.gz".format(self.jobid)
        remote_tfile = op.join(self.root_directory, "outputs", tfile)

        if not self.session.exists(remote_tfile):
            raise OrchestratorError("Expected output file does not exist: {}"
                                    .format(remote_tfile))

        with head_at(self.ds, self.head) as moved:
            with chpwd(self.ds.path):
                self.session.get(remote_tfile)
                with tarfile.open(tfile, mode="r:gz") as tar:
                    tar.extractall(path=".")
                os.unlink(tfile)
                # TODO: How to handle output cleanup on the remote?

                from datalad.interface.run import run_command
                lgr.info("Creating run commit in %s", self.ds.path)
                for res in run_command(
                        inputs=self.job_spec.get("inputs_unexpanded"),
                        extra_inputs=self.job_spec.get("extra_inputs"),
                        outputs=self.job_spec.get("outputs_unexpanded"),
                        inject=True,
                        extra_info={"reproman_jobid": self.jobid},
                        message=self.job_spec.get("message"),
                        cmd=self.job_spec["command_str_unexpanded"]):
                    # Oh, if only I were a datalad extension.
                    if res["status"] in ["impossible", "error"]:
                        raise OrchestratorError(
                            "Making datalad-run commit failed: {}"
                            .format(res["message"]))

                ref = self.job_refname
                if moved:
                    lgr.info("Results stored on %s. "
                             "Bring them into this branch with "
                             "'git merge %s'",
                             ref, ref)
                self.ds.repo.update_ref(ref, "HEAD")

        self.log_failed()


# Concrete orchestrators

# TODO: There's no support for non-shared file systems.


class PlainOrchestrator(
        PrepareRemotePlainMixin, FetchPlainMixin, Orchestrator):
    """Plain execution on remote directory.

    If no working directory is supplied via the `working_directory` job
    parameter, the remote directory is named with the job ID. Inputs are made
    available with a session.put(), and outputs are fetched with a
    session.get().

    Note: This orchestrator may be sufficient for simple tasks, but using one
    of the DataLad orchestrators is recommended.
    """

    name = "plain"
    template_name = "base"

    @property
    @cached_property
    @borrowdoc(Orchestrator)
    def working_directory(self):
        wdir = self.job_spec.get("working_directory")
        return wdir or op.join(self.root_directory, self.jobid)


class DataladPairOrchestrator(
        PrepareRemoteDataladMixin, FetchDataladPairMixin, DataladOrchestrator):
    """Execute command on remote dataset sibling.

    **Preparing the remote dataset** The default `working_directory` is the a
    directory named with dataset ID under `root_directory`. If the dataset
    doesn't exist, one is created, with a remote named after the resource.

    If the dataset already exists on the remote, the remote is updated, and the
    local commit is checked out on the remote. The orchestrator will check out
    a detached HEAD if needed. It won't proceed if the working tree is dirty
    and it won't advance a branch if it is checked out and the update is a
    fast-forward.

    To get inputs on the remote, a `datalad get` call is first tried to
    retrieve inputs from public sources. If that fails, a `datalad publish ...
    INPUTS` call from the local dataset to the remote dataset is performed.

    **Fetching a completed job** `datalad update` is called to bring in the
    remote changes, along with a `datalad get` call to fetch the specified
    outputs. On completion, the HEAD on the remote will be a commit recording
    changes from the run. It is marked with a git ref: refs/reproman/JOBID.
    """

    name = "datalad-pair"


class DataladPairRunOrchestrator(
        PrepareRemoteDataladMixin, FetchDataladRunMixin, DataladOrchestrator):
    """Execute command in remote dataset sibling and capture results locally as
    run record.

    The remote is prepared as described for the datalad-pair orchestrator.

    **Fetching a completed job** After the job completes on the remote, the
    outputs are bundled into a tarball. (Outputs are identified based on file
    time stamps, not on the specified outputs.) This tarball is downloaded to
    the local machine and used to create a `datalad run` commit. The local
    commit will be marked with a git ref: refs/reproman/JOBID.
    """

    name = "datalad-pair-run"


class DataladLocalRunOrchestrator(
        PrepareRemotePlainMixin, FetchDataladRunMixin, DataladOrchestrator):
    """Execute command in a plain remote directory and capture results locally
    as run record.

    This orchestrator is useful when the remote resource does not have DataLad
    installed. The remote is prepared as described for the plain orchestrator.
    The fetch is performed as described for the datalad-pair-run orchestrator.
    """

    name = "datalad-local-run"


ORCHESTRATORS = collections.OrderedDict(
    (o.name, o) for o in [
        PlainOrchestrator,
        DataladPairOrchestrator,
        DataladPairRunOrchestrator,
        DataladLocalRunOrchestrator,
    ]
)
