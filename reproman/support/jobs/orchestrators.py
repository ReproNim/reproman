# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrators for `reproman run`.
"""

import abc
import collections
import logging
import os
import os.path as op
import uuid
from tempfile import NamedTemporaryFile
import time

import six
from six.moves import map
from six.moves import shlex_quote

from reproman.dochelpers import borrowdoc
from reproman.utils import cached_property
from reproman.utils import chpwd
from reproman.resource.ssh import SSHSession
from reproman.support.jobs.submitters import SUBMITTERS
from reproman.support.jobs.template import Template
from reproman.support.exceptions import CommandError
from reproman.support.exceptions import MissingExternalDependency
from reproman.support.exceptions import OrchestratorError
from reproman.support.external_versions import external_versions

lgr = logging.getLogger("reproman.support.jobs.orchestrators")


# Abstract orchestrators


@six.add_metaclass(abc.ABCMeta)
class Orchestrator(object):
    """Base Orchestrator class.

    An Orchestrator is responsible for preparing a directory to run a command,
    submitting it with the specified submitter, and then handling the results.
    """

    template_name = None

    def __init__(self, resource, submission_type, job_spec=None):
        self.resource = resource
        self.session = resource.get_session()

        # TODO: Probe remote and try to infer.
        submitter_class = SUBMITTERS[submission_type or "local"]
        self.submitter = submitter_class(self.session)

        self.job_spec = job_spec or {}

        prev_id = self.job_spec.get("jobid")
        self.jobid = prev_id or "{}-{}".format(time.strftime("%Y%m%d-%H%M%S"),
                                               str(uuid.uuid4())[:4])

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

        By default, the working directory for a particular command should be a
        subdirectory of this directory. Orchestrators can also use this root to
        storing things outside of the working directory (e.g. artifacts used in
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
        pass

    @property
    @cached_property
    def meta_directory(self):
        """Directory used to store metadata for the run.
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
        return dict(to_dump, **self.template.kwds)

    @abc.abstractmethod
    def prepare_remote(self):
        """Prepare remote for run.
        """
        pass

    def _put_as_executable(self, text, target):
        with NamedTemporaryFile('w', prefix="reproman-", delete=False) as tfh:
            tfh.write(text)
        os.chmod(tfh.name, 0o755)
        self.session.put(tfh.name, target)
        os.unlink(tfh.name)

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
                six.text_type(exc) if err_msg is None else err_msg)
        return out

    def submit(self):
        """Submit the job with `submitter`.
        """
        lgr.info("Submitting %s", self.jobid)
        templ = Template(**dict(self.job_spec,
                                jobid=self.jobid,
                                root_directory=self.root_directory,
                                working_directory=self.working_directory,
                                meta_directory=self.meta_directory))
        self.template = templ
        self._put_as_executable(
            templ.render_runscript("{}.template.sh".format(
                self.template_name or self.name)),
            op.join(self.meta_directory, "runscript"))

        submission_file = op.join(self.meta_directory, "submit")
        self._put_as_executable(
            templ.render_submission("{}.template".format(self.submitter.name)),
            submission_file)

        subm_id = self.submitter.submit(submission_file)
        if subm_id is None:
            lgr.warning("No submission ID obtained for %s", self.jobid)
        else:
            lgr.info("Job %s submitted as %s job %s",
                     self.jobid, self.submitter.name, subm_id)
            self.session.execute_command("echo {} >{}".format(
                subm_id,
                op.join(self.meta_directory, "idmap")))

    @property
    def status(self):
        """Modify `submitter.status` with information from `status` file.
        """
        status_file = op.join(self.meta_directory, "status")
        status = "unknown"
        if self.session.exists(status_file):
            status = self.session.read(status_file).strip()
        return status

    @property
    def has_completed(self):
        """Has the run, including post-command processing, completed?
        """
        return self.session.exists(
            op.join(self.root_directory, "completed", self.jobid))

    def follow(self):
        """Follow command, exiting when post-command processing completes."""
        self.submitter.follow()
        # We're done according to the submitter. This includes the
        # post-processing. Make sure it looks like it passed.
        if not self.has_completed:
            raise OrchestratorError(
                "Post-processing failed for {} [status: {}] ({})"
                .format(self.jobid, self.status, self.working_directory))

    @abc.abstractmethod
    def fetch(self):
        """Fetch the submission result.
        """
        pass


def _datalad_check_container(ds, spec):
    """Adjust spec for `datalad-container`-configured container.

    If a "container" key is found, "command_str" will be replaced, and the
    previous "command_str" value will be placed under
    "command_str_nocontainer".
    """
    container = spec.get("container")
    if container is not None:

        def cfg_get(key):
            full_key = "datalad.containers.{}.{}".format(container, key)
            value = ds.config.get(full_key)
            if value is None:
                raise OrchestratorError(
                    "No value configured for {}".format(full_key))
            return value

        cmdexec = cfg_get("cmdexec")
        image = cfg_get("image")

        command_str = spec["command_str"]
        spec["commmand_str_nocontainer"] = command_str
        spec["command_str"] = cmdexec.format(img=image, cmd=command_str)

        # TODO: When datalad-container starts passing the image as
        # extra_inputs, we should handle that here (and in fetch below).
        inputs = spec.get("inputs", [])
        if image not in inputs:
            spec["inputs"] = inputs + [image]


def _datalad_format_command(ds, spec):
    """Adjust `spec` to use `datalad run`-style formatting.

    The "inputs", "outputs", and "command_str" keys in `spec` are replaced and
    the original are moved under the `*_unexpanded` key.
    """
    if "command_str_unexpanded" in spec:
        # Already adjust (most likely orchestrator is being resurrected).
        return
    from datalad.interface.run import format_command
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


@six.add_metaclass(abc.ABCMeta)
class DataladOrchestrator(Orchestrator):
    """Execute command assuming (at least) a local dataset.
    """

    def __init__(self, resource, submission_type, job_spec=None):
        if not external_versions["datalad"]:
            raise MissingExternalDependency(
                "DataLad is required for orchestrator '{}'".format(self.name))

        super(DataladOrchestrator, self).__init__(
            resource, submission_type, job_spec)

        from datalad.api import Dataset
        self.ds = Dataset(".")
        if not self.ds.id:
            raise OrchestratorError("orchestrator {} requires a local dataset"
                                    .format(self.name))

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

    @borrowdoc(Orchestrator)
    def as_dict(self):
        d = super(DataladOrchestrator, self).as_dict()
        d["dataset_id"] = self.ds.id
        return d


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

        inputs = self.job_spec.get("inputs")
        if not inputs:
            return

        for i in inputs:
            session.put(i, op.join(self.working_directory, op.basename(i)))


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

    def _assert_clean_repo(self):
        if self._execute_in_wdir("git status --porcelain"):
            raise OrchestratorError("Remote repository {} is dirty"
                                    .format(self.working_directory))

    def _checkout_target(self):
        target_commit = self.ds.repo.get_hexsha()
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
        if not self.session.exists(self.root_directory):
            self.session.mkdir(self.root_directory, parents=True)

        resource = self.resource
        session = self.session

        inputs = self.job_spec.get("inputs")
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
                since = ""

            self.ds.publish(to=resource.name, since=since, recursive=True)
            if inputs:
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
            else:
                self.session.execute_command(
                    "git push '{}' HEAD:refs/reproman/head"
                    .format(self.working_directory))

            if inputs:
                installed_ds = dl.Dataset(self.working_directory)
                installed_ds.get(inputs)
        else:
            # TODO: Handle more types?
            raise OrchestratorError("Unsupported resource type {}"
                                    .format(resource.type))

        self._assert_clean_repo()
        self._checkout_target()

        if not session.exists(self.meta_directory):
            session.mkdir(self.meta_directory, parents=True)


class FetchPlainMixin(object):

    def fetch(self):
        """Get outputs from remote.
        """
        outputs = self.job_spec.get("outputs")
        if not outputs:
            return

        for o in outputs:
            self.session.get(
                o if op.isabs(o) else op.join(self.working_directory, o),
                self.local_directory)


class FetchDataladPairMixin(object):

    def fetch(self):
        """Fetch the results from the remote dataset sibling.
        """
        lgr.info("Fetching results for %s", self.jobid)
        if self.resource.type == "ssh":
            # TODO: This won't work if _checkout_target() checked out a commit.
            self.ds.update(sibling=self.resource.name,
                           merge=True, recursive=True)
            outputs = self.job_spec.get("outputs")
            if outputs:
                self.ds.get(path=outputs)
        elif self.resource.type == "shell":
            # Below is just for local testing.  It doesn't support actually
            # getting the content.
            with chpwd(self.ds.path):
                self.session.execute_command(
                    ["git", "fetch", self.working_directory,
                     "refs/reproman/{0}:refs/reproman/{0}".format(self.jobid)])
                self.session.execute_command(
                    ["git", "merge", "FETCH_HEAD"])


class FetchDataladRunMixin(object):

    def fetch(self):
        """Fetch results tarball and inject run record into the local dataset.
        """
        lgr.info("Fetching results for %s", self.jobid)
        import tarfile
        tfile = "{}.tar.gz".format(self.jobid)
        remote_tfile = op.join(self.root_directory, "outputs", tfile)

        if not self.session.exists(remote_tfile):
            lgr.error("Expected output file %s does not exist", remote_tfile)
            return

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
                    outputs=self.job_spec.get("outputs_unexpanded"),
                    inject=True,
                    extra_info={"reproman_jobid": self.jobid},
                    message=self.job_spec.get("message"),
                    cmd=self.job_spec["command_str_unexpanded"]):
                # Oh, if only I were a datalad extension.
                pass


# Concrete orchestrators

# TODO: Need to polish and extend the orchestrators. The prepare_remote() and
# fetch() steps currently lack many safeguards and don't deal well with
# previous state. There's also no support for non-shared file systems.

# TODO: Improve the docstring descriptions of what the orchestrators do.


class PlainOrchestrator(
        PrepareRemotePlainMixin, FetchPlainMixin, Orchestrator):
    """Plain execution on remote directory.

    If no working directory is supplied, the remote directory is named with the
    job ID. Inputs are made available with a session.put(), and outputs are
    fetched with a session.get().
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
    """

    name = "datalad-pair"


class DataladPairRunOrchestrator(
        PrepareRemoteDataladMixin, FetchDataladRunMixin, DataladOrchestrator):
    """Execute command in remote dataset sibling and capture results locally as
    run record.
    """

    name = "datalad-pair-run"


class DataladLocalRunOrchestrator(
        PrepareRemotePlainMixin, FetchDataladRunMixin, DataladOrchestrator):
    """Execute command in a plain remote directory and capture results locally
    as run record."""

    name = "datalad-local-run"


ORCHESTRATORS = collections.OrderedDict(
    (o.name, o) for o in [
        PlainOrchestrator,
        DataladPairOrchestrator,
        DataladPairRunOrchestrator,
        DataladLocalRunOrchestrator,
    ]
)
