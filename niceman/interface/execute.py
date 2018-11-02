# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to run commands in an environment
"""

__docformat__ = 'restructuredtext'

import os
import os.path as op
import sys
import time
import uuid

from .base import Interface
from ..support.exceptions import CommandError
from ..support.exceptions import MissingExternalDependency
import niceman.interface.base  # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr
from ..support.external_versions import external_versions
from ..resource import get_manager
from ..resource.session import Session
from .common_opts import trace_opt
from .common_opts import resref_opt
from .common_opts import resref_type_opt

from logging import getLogger
lgr = getLogger('niceman.api.execute')


class CommandAdapter(object):
    """Interface to kinds of commands `exec` can execute.

    Each subclass should define an `execute` method and optionally define
    `pre_command` or `post_command` to perform pre- or post-command operations.
    The caller should execute the command by calling the instance object
    itself.

    Parameters
    ----------
    resource : Resource object
    command : str
        The program to run.
    cmd_args : list of str
        Arguments to pass to `command`.
    """

    def __init__(self, resource, command, cmd_args):
        self.resource = resource
        self.session = resource.get_session()
        self.command = command
        self.cmd_args = cmd_args

    def pre_command(self):
        pass

    def execute(self):
        """Run the full command defined by `command` and `cmd_args`.

        Returns
        -------
        A tuple, (stdout, stderr).
        """
        raise NotImplementedError

    def post_command(self):
        pass

    def __call__(self):
        self.pre_command()
        try:
            out, err = self.execute()
        finally:
            self.post_command()
        return out, err


class PlainCommand(CommandAdapter):

    def execute(self):
        return self.session.execute_command([self.command] + self.cmd_args)


class InternalCommand(CommandAdapter):

    def execute(self):
        self.session.niceman_exec(self.command, self.cmd_args)
        return None, None  # Return same form as Session.execute_command.


class TracedCommand(CommandAdapter):
    """A tracer-wrapped command.

    In the pre-command step, a tracer (extracted from ReproZip) is downloaded
    to the local machine if not already present.  This tracer is transferred to
    the resource on which the command will be executed.  This allows tracing on
    a remote resource that does not have ReproZip installed.

    After the command is executed under the tracer, the post-command step
    downloads the trace artifacts locally, uses ReproZip to write a
    configuration file from these artifacts, and then calls `niceman retrace`
    on the result..
    """

    def __init__(self, resource, command, cmd_args,
                 remote_dir=None, local_dir=None):
        super(TracedCommand, self).__init__(resource, command, cmd_args)

        if not external_versions["reprozip"]:
            raise MissingExternalDependency("Using --trace requires ReproZip, "
                                            "a Linux-specific dependency")

        self.tracer_md5sum = "d8561c1bc528592b21c0e28d6f32c0a4"
        # adding two random characters to avoid collisions etc
        # The id for the execution so we could pick up all the log and trace
        # files for local storage
        self.exec_id = "{}-{}".format(
            time.strftime("%Y%m%d%H%M%S"),
            str(uuid.uuid4())[:2])

        # Local session variables
        local_cache_dir = local_dir or op.expanduser('~/.cache/niceman')
        self.local_tracer_dir = op.join(local_cache_dir,
                                        "tracers",
                                        self.tracer_md5sum)
        self.local_trace_dir = op.join(local_cache_dir, 'traces', self.exec_id)
        self.local_tracer_gz = op.join(self.local_tracer_dir,
                                       "niceman_trace.gz")

        # Remote session variables
        self.remote_dir = remote_dir
        self.remote_trace_dir = None
        self.remote_tracer = None

    def _prepare_local(self):
        if not op.exists(self.local_tracer_gz):
            import hashlib
            import requests

            if not op.exists(self.local_tracer_dir):
                os.makedirs(self.local_tracer_dir)

            lgr.info("Downloading tracer...")
            resp = requests.get("https://github.com/ReproNim/reprozip/blob"
                                "/0497b229575c67219c5925360b6e63bf8d4d5eb9"
                                "/reprozip/native/rztracer.gz?raw=true",
                                allow_redirects=True)

            with open(self.local_tracer_gz, "wb") as stream:
                if self.tracer_md5sum != hashlib.md5(resp.content).hexdigest():
                    raise RuntimeError("md5sum for downloaded tracer "
                                       "does not match the expected one")
                stream.write(resp.content)
            lgr.info("Tracer downloaded to %s", self.local_tracer_gz)

    def _prepare_remote(self):
        # Establish a "management" session
        mng_ses = self.resource.get_session(pty=False)
        remote_env_full = mng_ses.query_envvars()
        root = self.remote_dir or '{HOME}/.cache'.format(**remote_env_full)
        remote_niceman_dir = '{}/niceman'.format(root)

        remote_traces_dir = op.join(remote_niceman_dir, 'traces')
        mng_ses.mkdir(remote_traces_dir, parents=True)
        self.remote_trace_dir = op.join(remote_traces_dir, self.exec_id)
        mng_ses.mkdir(self.remote_trace_dir, parents=True)

        remote_tracer_dir = op.join(remote_niceman_dir,
                                    "tracers",
                                    self.tracer_md5sum)
        # TODO: augment "entry point" somehow in a generic way?
        #    For interactive sessions with bash, we could overload ~/.bashrc
        #    to do our wrapping of actual call to bashrc under the "tracer"
        self.remote_tracer = op.join(remote_tracer_dir, "niceman_trace")

        if not self.session.exists(self.remote_tracer):
            remote_tracer_gz = self.remote_tracer + ".gz"
            # The gz file might already exist (e.g., a localshell session).
            if not self.session.exists(remote_tracer_gz):
                self.session.put(self.local_tracer_gz, remote_tracer_gz)
            self.session.execute_command(
                ["gunzip", "--keep", remote_tracer_gz])
            self.session.chmod(self.remote_tracer, "755")
        # TODO: might want to add also a "marker" so within the trace
        #       we could avoid retracing session establishing bits themselves

    def pre_command(self):
        self._prepare_local()
        self._prepare_remote()

    def execute(self):
        cmd_prefix = [
            self.remote_tracer,
            "--logfile", op.join(self.remote_trace_dir, "tracer.log"),
            "--dbfile", op.join(self.remote_trace_dir, "trace.sqlite3"),
            "--"
        ]
        return self.session.execute_command(
            cmd_prefix + [self.command] + self.cmd_args)

    def post_command(self):
        # Copy all the tracing artifacts here if not present already (e.g.
        # if session was a local shell)
        if not op.exists(self.local_trace_dir):
            for fname in ["tracer.log", "trace.sqlite3"]:
                self.session.get(op.join(self.remote_trace_dir, fname),
                                 op.join(self.local_trace_dir, fname))
            lgr.info(
                "Copied tracing artifacts under %s", self.local_trace_dir)
        else:
            lgr.debug(
                "Not copying %s from remote session "
                "since already exists locally",
                self.local_trace_dir)

        from reprozip.tracer.trace import write_configuration
        from rpaths import Path

        # we rely on hardcoded paths in reprozip
        write_configuration(
            directory=Path(self.local_trace_dir),
            sort_packages=False,
            find_inputs_outputs=True)

        from niceman.api import retrace
        niceman_spec_path = op.join(self.local_trace_dir, "niceman.yml")
        retrace(
            spec=op.join(self.local_trace_dir, "config.yml"),
            output_file=niceman_spec_path,
            resref=self.session
        )
        lgr.info("NICEMAN trace %s", niceman_spec_path)


# Exists for ease of testing.
CMD_CLASSES = {"plain": PlainCommand,
               "internal": InternalCommand,
               "trace": TracedCommand}


class Execute(Interface):
    """Execute a command in a computation environment

    Examples
    --------

      $ niceman execute mkdir /home/blah/data

    """

    _params_ = dict(
        command=Parameter(
            doc="name of the command to run",
            metavar='COMMAND',
            constraints=EnsureStr(),
        ),
        args=Parameter(
            doc="list of positional and keyword args to pass to the command",
            metavar='ARGS',
            nargs="*",
            constraints=EnsureStr(),
        ),
        resref=resref_opt,
        # XXX reenable when we support working with multiple instances at once
        # resource_type=Parameter(
        #     args=("-t", "--resource-type"),
        #     doc="""Resource type to work on""",
        #     constraints=EnsureStr(),
        # ),
        resref_type=resref_type_opt,
        # TODO: should be moved into generic API
        internal=Parameter(
            args=("--internal",),
            action="store_true",
            doc="Instead of running a generic/any command, execute the internal"
                " NICEMAN command available within sessions.  Known are: %s"
                % ', '.join(Session.INTERNAL_COMMANDS)
        ),
        trace=trace_opt,
    )

    @staticmethod
    def __call__(command, args, resref=None, resref_type="auto",
                 internal=False, trace=False):
        from niceman.ui import ui

        if internal and trace:
            raise NotImplementedError("No --trace for --internal commands")

        if not resref:
            resref = ui.question(
                "Enter a resource name or ID",
                error_message="Missing resource name or ID"
            )

        env_resource = get_manager().get_resource(resref, resref_type)
        env_resource.connect()

        if internal:
            cls_key = "internal"
        elif trace:
            cls_key = "trace"
        else:
            cls_key = "plain"
        cmd = CMD_CLASSES[cls_key](env_resource, command, args)

        try:
            error = None
            out, err = cmd()
        except CommandError as exc:
            error = exc
            out, err = exc.stdout, exc.stderr

        lgr.info("Executed the %s command in the environment %s", command,
                 env_resource.name)

        if out:
            sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
        if error:
            lgr.error(
                "Command %s failed to run in %s: %s",
                command, env_resource.name, error.msg
            )
            raise SystemExit(error.code)
