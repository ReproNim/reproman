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
import niceman.interface.base  # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from ..resource import get_manager
from ..resource.session import Session
from .common_opts import trace_opt
from .common_opts import resref_opt
from .common_opts import resref_type_opt

from logging import getLogger
lgr = getLogger('niceman.api.exec')


class Exec(Interface):
    """Make a directory in a computation environment

    Examples
    --------

      $ niceman exec mkdir /home/blah/data

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
        if not resref:
            resref = ui.question(
                "Enter a resource name or ID",
                error_message="Missing resource name or ID"
            )

        env_resource = get_manager().get_resource(resref, resref_type)
        env_resource.connect()
        session = env_resource.get_session()

        remote_env = {}
        cmd_prefix = []

        # adding two random characters to avoid collisions etc
        # The id for the execution so we could pick up all the log and trace
        # files for local storage
        exec_id = "{}-{}".format(
            time.strftime("%Y%m%d%H%M%S"),
            str(uuid.uuid4())[:2])

        if trace:
            local_cache_dir = op.expanduser('~/.cache/niceman')
            tracer_md5sum = "d8561c1bc528592b21c0e28d6f32c0a4"
            local_tracer_dir = op.join(local_cache_dir, "tracers",
                                       tracer_md5sum)
            local_tracer_gz = op.join(local_tracer_dir, "niceman_trace.gz")

            if not op.exists(local_tracer_gz):
                import hashlib
                import requests

                if not op.exists(local_tracer_dir):
                    os.makedirs(local_tracer_dir)
                resp = requests.get("https://github.com/ReproNim/reprozip/blob"
                                    "/0497b229575c67219c5925360b6e63bf8d4d5eb9"
                                    "/reprozip/native/rztracer.gz?raw=true",
                                    allow_redirects=True)

                with open(local_tracer_gz, "wb") as stream:
                    if tracer_md5sum != hashlib.md5(resp.content).hexdigest():
                        raise RuntimeError("md5sum for downloaded tracer "
                                           "does not match the expected one")
                    stream.write(resp.content)

            # Establish a "management" session first
            mng_ses = env_resource.get_session(pty=False)
            remote_env_full = mng_ses.query_envvars()
            remote_niceman_dir = \
                '{HOME}/.cache/niceman'.format(**remote_env_full)
            remote_traces_dir = op.join(remote_niceman_dir, 'traces')
            remote_tracer_dir = op.join(remote_niceman_dir, "tracers",
                                        tracer_md5sum)

            mng_ses.mkdir(remote_tracer_dir, parents=True)
            remote_env['NICEMAN_TRACE_DIR'] = \
                remote_trace_dir = \
                op.join(remote_traces_dir, exec_id)
            mng_ses.mkdir(remote_trace_dir, parents=True)

            # TODO: augment "entry point" somehow in a generic way?
            #    For interactive sessions with bash, we could overload ~/.bashrc
            #    to do our wrapping of actual call to bashrc under the "tracer"
            remote_tracer = op.join(remote_tracer_dir, "niceman_trace")
            if not session.exists(remote_tracer):
                remote_tracer_gz = remote_tracer + ".gz"
                # The gz file might already exist (e.g., a localshell session).
                if not session.exists(remote_tracer_gz):
                    session.put(local_tracer_gz, remote_tracer_gz)
                session.execute_command(["gunzip", "--keep", remote_tracer_gz])
                session.chmod(remote_tracer, "755")
            cmd_prefix = [
                remote_tracer,
                "--logfile", op.join(remote_trace_dir, "tracer.log"),
                "--dbfile", op.join(remote_trace_dir, "trace.sqlite3"),
                "--"
            ]
            # TODO: might want to add also a "marker" so within the trace
            #       we could avoid retracing session establishing bits themselves
            pass

        # TODO: collect logs into an exec_id directory

        try:
            error = None
            out, err = None, None
            if internal:
                if trace:
                    raise NotImplementedError("No --trace for --internal commands")
                session.niceman_exec(command, args)
            else:
                out, err = session.execute_command(cmd_prefix + [command] + args)  # , env=remote_env)
        except CommandError as exc:
            error = exc
            out, err = exc.stdout, exc.stderr

        if trace:
            # Copy all the tracing artifacts here if not present already (e.g.
            # if session was a local shell)
            local_trace_dir = op.join(local_cache_dir, 'traces', exec_id)
            if not op.exists(local_trace_dir):
                for fname in ["tracer.log", "trace.sqlite3"]:
                    session.get(op.join(remote_trace_dir, fname),
                                op.join(local_trace_dir, fname))
                lgr.info(
                    "Copied tracing artifacts under %s", local_trace_dir)
            else:
                lgr.debug(
                    "Not copying %s from remote session since already exists locally",
                    local_trace_dir)

            try:
                from reprozip.tracer.trace import write_configuration
            except ImportError:
                raise RuntimeError("Using --trace requires ReproZip, "
                                   "a Linux-specific dependency")
            from rpaths import Path

            # we rely on hardcoded paths in reprozip
            write_configuration(
                directory=Path(local_trace_dir),
                sort_packages=False,
                find_inputs_outputs=True)

            from niceman.api import retrace
            niceman_spec_path = op.join(local_trace_dir, "niceman.yml")
            retrace(
                spec=op.join(local_trace_dir, "config.yml"),
                output_file=niceman_spec_path,
                resource=session
            )
            lgr.info("NICEMAN trace %s", niceman_spec_path)


        lgr.info("Executed the %s command in the environment %s", command,
                 env_resource.name)

        if out:
            sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
        if error:
            lgr.error(
                "Command %s failed to run in %s",
                command, env_resource
            )
            raise SystemExit(error.code)