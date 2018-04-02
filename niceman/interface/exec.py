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

import os.path as op
import time
import uuid

from .base import Interface
import niceman.interface.base # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from ..resource import ResourceManager
from ..resource.session import Session
from .common_opts import trace_opt

from logging import getLogger
lgr = getLogger('niceman.api.exec')


class Exec(Interface):
    """Make a directory in a computation environment

    Examples
    --------

      $ niceman exec mkdir /home/blah/data --config=niceman.cfg

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
        name=Parameter(
            args=("-n", "--name"),
            doc="""Name of the resource to consider. To see
            available resource, run the command 'niceman ls'""",
            # constraints=EnsureStr(),
        ),
        # XXX reenable when we support working with multiple instances at once
        # resource_type=Parameter(
        #     args=("-t", "--resource-type"),
        #     doc="""Resource type to work on""",
        #     constraints=EnsureStr(),
        # ),
        resource_id=Parameter(
            args=("-id", "--resource-id",),
            doc="ID of the environment container",
            # constraints=EnsureStr(),
        ),
        # TODO: should be moved into generic API
        config=Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            # constraints=EnsureStr(),
        ),
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
    def __call__(command, args, name=None, resource_id=None, config=None,
                 internal=False, trace=False):
        from niceman.ui import ui
        if not name and not resource_id:
            name = ui.question(
                "Enter a resource name",
                error_message="Missing resource name"
            )

        # Get configuration and environment inventory
        # TODO: this one would ask for resource type whenever it is not found
        #       why should we???
        resource_info, inventory = ResourceManager.get_resource_info(config,
            name, resource_id)

        # Delete resource environment
        env_resource = ResourceManager.factory(resource_info)
        env_resource.connect()

        if not env_resource.id:
            raise ValueError("No resource found given the info %s" % str(resource_info))

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
            # Establish a "management" session first
            mng_ses = env_resource.get_session(pty=False)
            remote_env_full = mng_ses.query_envvars()
            remote_niceman_dir = \
                '{HOME}/.cache/niceman'.format(**remote_env_full)
            remote_traces_dir = op.join(remote_niceman_dir, 'traces')
            remote_tracer_dir = op.join(remote_niceman_dir, 'tracer')

            mng_ses.mkdir(remote_tracer_dir, parents=True)
            remote_env['NICEMAN_TRACE_DIR'] = \
                remote_trace_dir = \
                op.join(remote_traces_dir, exec_id)
            mng_ses.mkdir(remote_trace_dir, parents=True)

            # TODO: deposit the tracer if not there yet
            # TODO: augment "entry point" somehow in a generic way?
            #    For interactive sessions with bash, we could overload ~/.bashrc
            #    to do our wrapping of actual call to bashrc under the "tracer"
            remote_tracer = op.join(remote_tracer_dir, "niceman_trace")
            if not session.exists(remote_tracer):
                session.put(
                    "/home/yoh/proj/repronim/reprozip/reprozip/native/rztracer",
                    remote_tracer)
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

        if internal:
            if trace:
                raise NotImplementedError("No --trace for --internal commands")
            session.niceman_exec(command, args)
        else:
            session.execute_command(cmd_prefix + [command] + args, env=remote_env)

        if trace:
            # Copy all the tracing artifacts here if not present already (e.g.
            # if session was a local shell)
            local_trace_dir = op.join(
                op.expanduser('~/.cache/niceman'), 'traces', exec_id)
            if not op.exists(local_trace_dir):
                session.get(remote_trace_dir, local_trace_dir)
            else:
                lgr.debug(
                    "Not copying %s from remote session since already exists locally",
                    local_trace_dir)

        ResourceManager.set_inventory(inventory)

        lgr.info("Executed the %s command in the environment %s", command,
                 name)