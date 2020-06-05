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
import json
import logging
import os
import os.path as op
import uuid
from tempfile import NamedTemporaryFile
import time
import yaml

from shlex import quote as shlex_quote

import reproman
from reproman.dochelpers import borrowdoc
from reproman.dochelpers import exc_str
from reproman.utils import cached_property
from reproman.utils import chpwd
from reproman.utils import write_update
from reproman.resource.shell import ShellSession
from reproman.resource.ssh import SSHSession
from reproman.support.jobs.submitters import SUBMITTERS
from reproman.support.jobs.template import Template
from reproman.support.exceptions import CommandError
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
        orchestrator looks here for other required values, like "_jobid".

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
            important_keys = ["_jobid", "root_directory", "working_directory",
                              "local_directory"]
            for key in important_keys:
                if key not in self.job_spec:
                    raise OrchestratorError(
                        "Job spec must have key '{}' to resurrect orchestrator"
                        .format(key))

            self.jobid = self.job_spec["_jobid"]
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
                   "_submission_id": self.submitter.submission_id,
                   "_reproman_version": reproman.__version__,
                   # For spec version X.Y, X should be incremented if there is
                   # a incompatible change to the format. Y may optionally be
                   # incremented to signal a compatible change (e.g., a new
                   # field is added, but the code doesn't require it).
                   "_spec_version": "1.0"}
        return dict(self.template.kwds if self.template else {},
                    **to_dump)

    def _prepare_spec(self):
        """Prepare the spec for the run.

        At the moment, this involves constructing the "_command_array",
        "_inputs_array", and "_outputs_array" keys.
        """
        from reproman.support.globbedpaths import GlobbedPaths

        spec = self.job_spec
        if spec.get("_resolved_batch_parameters"):
            raise OrchestratorError(
                "Batch parameters are currently only supported "
                "in DataLad orchestrators")

        for key in ["inputs", "outputs"]:
            if key in spec:
                gp = GlobbedPaths(spec[key])
                spec["_{}_array".format(key)] = [gp.expand(dot=False)]
        if "_resolved_command_str" in spec:
            spec["_command_array"] = [spec["_resolved_command_str"]]
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
                   _jobid=self.jobid,
                   _num_subjobs=len(self.job_spec["_command_array"]),
                   root_directory=self.root_directory,
                   working_directory=self.working_directory,
                   _meta_directory=self.meta_directory,
                   _meta_directory_rel=op.relpath(self.meta_directory,
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

        self._put_text(
            "\0".join(self.job_spec["_command_array"]),
            op.join(self.meta_directory, "command-array"))

        self._put_text(
            yaml.safe_dump(self.as_dict()),
            op.join(self.meta_directory, "spec.yaml"))

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
        # FIXME: How to handle subjobs?
        return self.get_status()

    @property
    def has_completed(self):
        """Has the run, including post-command processing, completed?
        """
        return self.session.exists(
            op.join(self.root_directory, "completed", self.jobid))

    def get_failed_subjobs(self):
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
        # FIXME: This will be inaccurate for PBS. Uses "-" rather than ".".
        lgr.info("%s stderr: %s",
                 jobid,
                 op.join(metadir, "stderr." + stderr_suffix))

    def log_failed(self, failed=None, func=None):
        """Display a log message about failed status.

        Parameters
        ----------
        failed : list of int, optional
            Failed subjobs.
        func : callable or None, optional
            If a failed status is detected, call this function with two
            arguments, the local metadata directory and a list of failed
            subjobs.
        """
        failed = failed or self.get_failed_subjobs()
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
                "Runscript handling failed for {} [status: {}]\n"
                "Check error logs in {}"
                .format(self.jobid, self.status, self.meta_directory))

    def _get_io_set(self, which, subjobs):
        spec = self.job_spec
        if subjobs is None:
            subjobs = range(len(spec["_command_array"]))
        key = "_{}_array".format(which)
        values = spec.get(key)
        if not values:
            return set()
        return {fname for i in subjobs for fname in values[i]}

    def get_inputs(self, subjobs=None):
        """Return input files.

        Parameters
        ----------
        subjobs : iterable of int or None
            Restrict results to these subjobs.

        Returns
        -------
        Set of str
        """
        return self._get_io_set("inputs", subjobs).union(
            self._get_io_set("extra_inputs", subjobs))

    def get_outputs(self, subjobs=None):
        """Return output files.

        Parameters
        ----------
        subjobs : iterable of int or None
            Restrict results to these subjobs.

        Returns
        -------
        Set of str
        """
        return self._get_io_set("outputs", subjobs)

    @abc.abstractmethod
    def fetch(self, on_remote_finish=None):
        """Fetch the submission result.

        In addition to doing whatever is need to fetch the results, this method
        should call `self.log_failed` right before it's finished working with
        the resource. Once finished with the resource, it should call
        `on_remote_finish`.
        """


def _datalad_check_container(ds, spec):
    """Adjust spec for `datalad-container`-configured container.

    If a "container" key is found, a new key "_container_command_str" will be
    added with the container-formatted command.
    """
    container = spec.get("container")
    if container is not None:
        # TODO: This is repeating too much logic from containers-run. Consider
        # reworking datalad-container to enable outside use.
        external_versions.check("datalad_container", min_version="0.4.0")
        from datalad_container.containers_run import get_command_pwds
        from datalad_container.find_container import find_container

        try:
            cinfo = find_container(ds, container)
        except ValueError as exc:
            raise OrchestratorError(exc)

        cmdexec = cinfo["cmdexec"]
        image = op.relpath(cinfo["path"], ds.path)

        pwd, _ = get_command_pwds(ds)
        image_dspath = op.relpath(cinfo.get('parentds', ds.path), pwd)

        spec["_container_command_str"] = cmdexec.format(
            img=image,
            cmd=spec["_resolved_command_str"],
            img_dspath=image_dspath)
        spec["_extra_inputs"] = [image]


def _datalad_format_command(ds, spec):
    """Adjust `spec` to use `datalad run`-style formatting.

    Create "*_array" keys and format commands with DataLad's `format_command`.
    """
    from datalad.core.local.run import format_command
    # DataLad's GlobbedPaths _should_ be the same as ours, but let's use
    # DataLad's to avoid potential discrepancies with datalad-run's behavior.
    from datalad.core.local.run import GlobbedPaths

    batch_parameters = spec.get("_resolved_batch_parameters") or [{}]
    spec["_command_array"] = []
    spec["_inputs_array"] = []
    spec["_outputs_array"] = []
    for cp in batch_parameters:
        fmt_kwds = {}
        for key in ["inputs", "outputs"]:
            if key in spec:
                parametrized = [io.format(p=cp) for io in spec[key]]
                gp = GlobbedPaths(parametrized)
                spec["_{}_array".format(key)].append(gp.expand(dot=False))
                fmt_kwds[key] = gp
        fmt_kwds["p"] = cp
        cmd_str = spec.get("_container_command_str",
                           spec["_resolved_command_str"])
        spec["_command_array"].append(format_command(ds, cmd_str, **fmt_kwds))

    exinputs = spec.get("_extra_inputs", [])
    spec["_extra_inputs_array"] = [exinputs] * len(batch_parameters)


class DataladOrchestrator(Orchestrator, metaclass=abc.ABCMeta):
    """Execute command assuming (at least) a local dataset.
    """

    def __init__(self, resource, submission_type, job_spec=None,
                 resurrection=False):
        external_versions.check("datalad", min_version="0.13")
        super(DataladOrchestrator, self).__init__(
            resource, submission_type, job_spec, resurrection=resurrection)

        from datalad.api import Dataset
        self.ds = Dataset(".")
        if not self.ds.id:
            raise OrchestratorError("orchestrator {} requires a local dataset"
                                    .format(self.name))

        if self._resurrection:
            self.head = self.job_spec.get("_head")
        else:
            if self.ds.repo.dirty:
                raise OrchestratorError("Local dataset {} is dirty. "
                                        "Save or discard uncommitted changes"
                                        .format(self.ds.path))
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
        d["_dataset_id"] = self.ds.id
        d["_head"] = self.head
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

        self.ds.save([gitignore, gitattrs],
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
    return "ssh://{user}{host}{port}{path}".format(
        user=user + "@" if user else "",
        host=host,
        port=":" + str(port) if port is not None else "",
        path=path)


class PrepareRemoteDataladMixin(object):

    def _execute_in_wdir(self, command, err_msg=None):
        """Helper to run command in remote working directory.

        Parameters
        ----------
        command : list of str or str
        err_msg : optional
            Message to use if an OrchestratorError is raised.

        Returns
        -------
        standard output

        Raises
        ------
        OrchestratorError if command fails.
        """
        try:
            out, _ = self.session.execute_command(
                command,
                cwd=self.working_directory)
        except CommandError as exc:
            raise OrchestratorError(
                str(exc) if err_msg is None else err_msg)
        return out

    def _execute_datalad_json_command(self, subcommand):
        out = self._execute_in_wdir(["datalad", "-f", "json"] + subcommand)
        return map(json.loads, out.splitlines())

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
                        # FIXME: How to handle subjobs?
                        op.relpath(op.join(self.meta_directory, "status.0"),
                                   self.working_directory)))
            status = status_from_ref.strip() or status
        return status

    def get_failed_subjobs(self):
        """Like Orchestrator.get_failed_subjobs, but inspect the job's git ref if needed.
        """
        failed = super(DataladOrchestrator, self).get_failed_subjobs()
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
                # Line format: mode<SP>type<SP>object<TAB>filename
                failed = [int(ln.split("\t")[1])
                          for ln in failed_ref.strip().splitlines()]
        return failed

    def _assert_clean_repo(self, cwd=None):
        cmd = ["git", "status", "--porcelain",
               "--ignore-submodules=all", "--untracked-files=normal"]
        out, _ = self.session.execute_command(
            cmd, cwd=cwd or self.working_directory)
        if out:
            raise OrchestratorError("Remote repository {} is dirty"
                                    .format(cwd or self.working_directory))

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

    def _fix_up_dataset(self):
        """Try to get datataset and subdatasets into the correct state.
        """
        self._checkout_target()
        # fixup 0: 'datalad create-sibling --recursive' leaves the subdataset
        # uninitialized (see DataLad's 78e00dcd2).
        self._execute_in_wdir(["git", "submodule", "update", "--init"])

        # fixup 1: Check out target commit in subdatasets. This should later be
        # replaced by the planned Datalad functionality to get an entire
        # dataset hierarchy to a recorded state.
        #
        # fixup 2: Autoenable remotes:
        # 'datalad publish' does not autoenable remotes, and 'datalad
        # create-sibling' calls 'git annex init' too early to trigger
        # autoenabling. Temporarily work around this issue, though this
        # should very likely be addressed in DataLad. And if this is here
        # to stay, we should avoid this call for non-annex datasets.
        lgr.info("Adjusting state of remote dataset")
        self._execute_in_wdir(["git", "annex", "init"])
        for res in self._execute_datalad_json_command(
                ["subdatasets", "--fulfilled=true", "--recursive"]):
            cwd = res["path"]
            self._assert_clean_repo(cwd=cwd)
            lgr.debug("Adjusting state of %s", cwd)
            cmds = [["git", "checkout", res["revision"]],
                    ["git", "annex", "init"]]
            for cmd in cmds:
                try:
                    out, _ = self.session.execute_command(
                        cmd, cwd=cwd)
                except CommandError as exc:
                    raise OrchestratorError(str(exc))

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
        if isinstance(session, (SSHSession, ShellSession)):
            if isinstance(session, SSHSession):
                if resource.key_filename:
                    # Make the identity file available to 'datalad sshrun' even
                    # if it is not configured in .ssh/config. This is
                    # particularly important for AWS keys.
                    os.environ["DATALAD_SSH_IDENTITYFILE"] = resource.key_filename
                    from datalad import cfg
                    cfg.reload(force=True)

                target_path = _format_ssh_url(
                    resource.user,
                    # AWS resource does not have host attribute.
                    getattr(resource, "host", None) or session.connection.host,
                    getattr(resource, "port", None),
                    self.working_directory)
            else:
                target_path = self.working_directory

            # TODO: Add one level deeper with reckless clone per job to deal
            # with concurrent jobs?
            if not session.exists(self.working_directory):
                remotes = self.ds.repo.get_remotes()
                if resource.name in remotes:
                    raise OrchestratorError(
                        "Remote '{}' unexpectedly exists. "
                        "Either delete remote or rename resource."
                        .format(resource.name))

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

            self.ds.create_sibling(target_path, name=resource.name,
                                   recursive=True, existing="skip")

            for res in self.ds.publish(to=resource.name, since=since,
                                       recursive=True, on_failure="ignore"):
                lgr.debug("datalad publish result: %s", res)
                if res["status"] == "error":
                    raise OrchestratorError(
                        "'datalad publish' failed: {}"
                        .format(res))

            self._fix_up_dataset()

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
        else:
            # TODO: Handle more types?
            raise OrchestratorError("Unsupported resource type {}"
                                    .format(resource.type))

        if not session.exists(self.meta_directory):
            session.mkdir(self.meta_directory, parents=True)


class FetchPlainMixin(object):

    def fetch(self, on_remote_finish=None):
        """Get outputs from remote.

        Parameters
        ----------
        on_remote_finish : callable, optional
            Function to be called when work with the resource is finished. It
            will be passed two arguments, the resource and the failed subjobs
            (list of ints).
        """
        lgr.info("Fetching results for %s", self.jobid)
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

        failed = self.get_failed_subjobs()
        self.log_failed(failed, func=get_failed_meta)

        lgr.info("Outputs fetched. Finished with remote resource '%s'",
                 self.resource.name)
        if on_remote_finish:
            on_remote_finish(self.resource, failed)


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
            # Note: It's tempting try to use --recurse-submodules here, but
            # that will absorb submodule's .git/ directories, and DataLad
            # relies on plain .git/ directories.
            if dataset.repo.dirty:
                raise OrchestratorError(
                    "Refusing to move HEAD due to submodule state change "
                    "within {}".format(dataset.path))
            yield moved
        finally:
            lgr.info("Restoring checkout of %s", to_restore)
            dataset.repo.checkout(to_restore)
    else:
        yield moved


class FetchDataladPairMixin(object):

    def fetch(self, on_remote_finish=None):
        """Fetch the results from the remote dataset sibling.

        Parameters
        ----------
        on_remote_finish : callable, optional
            Function to be called when work with the resource is finished. It
            will be passed two arguments, the resource and the failed subjobs
            (list of ints).
        """
        from datalad.support.exceptions import CommandError as DCError

        lgr.info("Fetching results for %s", self.jobid)
        failed = self.get_failed_subjobs()
        resource_name = self.resource.name
        ref = self.job_refname
        lgr.info("Updating local dataset with changes from '%s'",
                 resource_name)
        self.ds.repo.fetch(resource_name, "{0}:{0}".format(ref),
                           recurse_submodules="no")
        failure = False
        try:
            self.ds.repo.merge(ref)
        except DCError as exc:
            lgr.warning(
                "Failed to merge in changes from %s. "
                "Check %s for merge conflicts. %s",
                ref, self.ds.path, exc_str(exc))
        else:
            # Handle any subdataset updates. We could avoid this if we knew
            # there were no subdataset changes, but it's probably simplest to
            # just unconditionally call update().
            for res in self.ds.update(
                    sibling=resource_name,
                    merge=True, follow="parentds", recursive=True,
                    on_failure="ignore"):
                if res["status"] == "error":
                    # DataLad will log failure.
                    failure = True

        if not failure:
            lgr.info("Getting outputs from '%s'", resource_name)
            outputs = list(self.get_outputs())
            if outputs:
                self.ds.get(path=outputs)

        self.log_failed(failed,
                        func=lambda mdir, _: self.ds.get(path=mdir))

        lgr.info("Finished with remote resource '%s'", resource_name)
        if on_remote_finish:
            on_remote_finish(self.resource, failed)


class FetchDataladRunMixin(object):

    def fetch(self, on_remote_finish=None):
        """Fetch results tarball and inject run record into the local dataset.

        on_remote_finish : callable, optional
            Function to be called when work with the resource is finished. It
            will be passed two arguments, the resource and the failed subjobs
            (list of ints).
        """
        lgr.info("Fetching results for %s", self.jobid)
        import tarfile
        tfile = "{}.tar.gz".format(self.jobid)
        remote_tfile = op.join(self.root_directory, "outputs", tfile)

        if not self.session.exists(remote_tfile):
            raise OrchestratorError("Expected output file does not exist: {}"
                                    .format(remote_tfile))

        failed = self.get_failed_subjobs()
        with head_at(self.ds, self.head) as moved:
            with chpwd(self.ds.path):
                resource_name = self.resource.name
                lgr.info("Fetching output tarball from '%s'", resource_name)
                self.session.get(remote_tfile)
                # This log_failed() may mention files that won't be around
                # until the tarball extraction below, but we do call
                # log_failed() now because it might need the remote resource
                # and we want to finish up with remote operations.
                self.log_failed(failed)

                lgr.info("Finished with remote resource '%s'", resource_name)
                if on_remote_finish:
                    on_remote_finish(self.resource, failed)
                lgr.info("Extracting output tarball into local dataset '%s'",
                         self.ds.path)
                with tarfile.open(tfile, mode="r:gz") as tar:
                    tar.extractall(path=".")
                os.unlink(tfile)
                # TODO: How to handle output cleanup on the remote?

                from datalad.core.local.run import run_command
                lgr.info("Creating run commit in %s", self.ds.path)

                cmds = self.job_spec["_command_array"]
                if len(cmds) == 1:
                    cmd = cmds[0]
                else:
                    # FIXME: Can't use unexpanded command because of unknown
                    # placeholders.
                    cmd = self.jobid

                for res in run_command(
                        # FIXME: How to represent inputs and outputs given that
                        # they are formatted per subjob and then expanded by
                        # glob?
                        inputs=self.job_spec.get("inputs"),
                        extra_inputs=self.job_spec.get("_extra_inputs"),
                        outputs=self.job_spec.get("outputs"),
                        inject=True,
                        extra_info={"reproman_jobid": self.jobid},
                        message=self.job_spec.get("message"),
                        cmd=cmd):
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
