# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of a Singularity environment."""

import os
import logging
from shlex import quote as shlex_quote

import attr

from ..cmd import Runner
from ..dochelpers import borrowdoc
from ..support.exceptions import CommandError, OutdatedExternalDependency
from ..support.external_versions import external_versions
from .session import POSIXSession, Session
from .base import Resource
from ..utils import attrib
from ..utils import command_as_string

lgr = logging.getLogger('reproman.resource.singularity')  # pylint: disable=C0103


@attr.s
class Singularity(Resource):
    """
    Environment manager which manages a Singularity container.
    """

    # Generic properties of any Resource
    name = attrib(default=attr.NOTHING)
    image = attrib(doc="Base image filename or url", default=attr.NOTHING)

    # Container properties
    id = attrib()
    type = attrib(default='singularity')

    status = attrib()
    _runner = Runner()

    def connect(self):
        """
        Open a connection to the environment.
        """
        external_versions.check("cmd:singularity", min_version="2.4")
        # # TODO(asmacdo) naive attempt but this fails on apptainer with
        # # reproman.support.exceptions.CommandError: CommandError: command '['singularity', 'instance.start', 'docker://python:2.7', '3a7bf62ebd9']' failed with ex...
        # try:
        #     external_versions.check("cmd:singularity", min_version="2.4")
        # except OutdatedExternalDependency:
        #     # singularity went back to 1.0 when name changed to apptainer
        #     external_versions.check("cmd:apptainer", min_version="1.0")
        # Get instance info if we have one running.
        info = self.get_instance_info()
        if info:
            if not self.name:
                self.name = info['name']
            if not self.id:
                self.id = "{name}-{pid}".format(**info)  # pylint: disable=C0103
            self.image = info['image']
            self.status = 'running'
        else:
            self.id = None
            self.status = None

    def _run_instance_command(self, cmd, args=None, **kwargs):
        """Singularity 3.x changed from "instance.cmd" to just "instance cmd"
        This is a helper to centralize execution
        """
        cmd = ['instance.%s' % cmd] \
            if external_versions['cmd:singularity'] < '3' \
            else ['instance', cmd]
        return self._runner.run(['singularity'] + cmd + (args or []), **kwargs)

    def create(self):
        """
        Create a container instance.

        Yields
        -------
        dict : config parameters to capture in the inventory file
        """
        # Check to see if the container is already running.
        info = self.get_instance_info()
        if info:
            lgr.info("Resource '%s' already exists.", self.name)
        else:
            # Start the container instance.
            # NOTE: Logging stdout and stderr hangs the run call, so we
            # disable the logging in the run call below.
            self._run_instance_command(
                'start', [self.image, self.name],
                log_stdout=False, log_stderr=False
            )
            info = self.get_instance_info()

        # Update status
        self.id = "{name}-{pid}".format(**info)
        self.status = 'running'
        yield {
            'id': self.id,
            'status': self.status
        }

    def delete(self):
        """
        Deletes a container instance.
        """
        # Check to see if the container is already stopped.
        if not self.get_instance_info():
            return

        # Stop the container.
        self._run_instance_command('stop', [self.name])

        # Update status
        self.id = None
        self.status = None

    def start(self):
        """
        Start a stopped container.
        """
        # Not a Singularity feature
        raise NotImplementedError

    def stop(self):
        """
        Stop a running container.
        """
        # Not a Singularity feature
        raise NotImplementedError

    @borrowdoc(Resource)
    def get_session(self, pty=False, shared=None):
        if not self.get_instance_info():
            self.connect()

        if pty and shared is not None and not shared:
            lgr.warning("Cannot do non-shared pty session for Singularity yet")
        return (PTYSingularitySession if pty else SingularitySession)(
            name=self.name
        )

    def get_instance_info(self):
        """
        Return basic information about a running container

        Returns
        -------
        None or dict
          instance info
        """
        try:
            stdout, _ = self._run_instance_command('list', expect_fail=True)
        except CommandError:
            return None

        # Parse stdout to find the running instance.
        # The output of instance.list is a table with columns:
        #   DAEMON NAME, PID, and CONTAINER IMAGE
        # Daemon names are unique on each server.
        for row in stdout.strip().splitlines()[1:]:
            items = row.split()
            if self.name == items[0] or self.id == "{0}-{1}".format(*items):
                return {
                    'name': items[0],  # daemon name
                    'pid': items[1],   # daemon process id
                    'image': items[2]  # container image file
                }
        return None


@attr.s
class SingularitySession(POSIXSession):
    """Non-interactive Singularity session"""

    name = attrib(default=attr.NOTHING)
    _runner = Runner()

    @borrowdoc(Session)
    def _execute_command(self, command, env=None, cwd=None, with_shell=True):
        command = self._prefix_command(command_as_string(command), env=env,
                                        cwd=cwd, with_shell=with_shell)
        lgr.debug('Running command %r', command)
        stdout, stderr = self._runner.run(
            "singularity exec instance://{} {}".format(self.name, command),
            expect_fail=True)

        return (stdout, stderr)

    def _put_file(self, src_path, dest_path):
        dest_path = self._prepare_dest_path(src_path, dest_path,
                                            local=False, absolute_only=True)
        cmd = 'cat {} | singularity exec instance://{} tee {} > /dev/null'
        self._runner.run(cmd.format(shlex_quote(src_path),
                                    self.name,
                                    shlex_quote(dest_path)))

    @borrowdoc(Session)
    def put(self, src_path, dest_path, uid=-1, gid=-1):
        self.transfer_recursive(
            src_path, 
            dest_path, 
            os.path.isdir, 
            os.listdir, 
            self.mkdir, 
            self._put_file
        )

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid, recursive=True)

    def _get_file(self, src_path, dest_path):
        dest_path = self._prepare_dest_path(src_path, dest_path)
        cmd = 'singularity exec instance://{} cat {} > {}'
        self._runner.run(cmd.format(self.name,
                                    shlex_quote(src_path),
                                    shlex_quote(dest_path)))

    @borrowdoc(Session)
    def get(self, src_path, dest_path=None, uid=-1, gid=-1):
        self.transfer_recursive(
            src_path, 
            dest_path, 
            self.isdir, 
            self.listdir, 
            os.mkdir, 
            self._get_file
        )

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid, remote=False, recursive=True)

    def listdir(self, path):
        cmd = ['singularity', 
                'exec', 
               'instance://{}'.format(self.name), 
               'ls', 
               '-1', 
               path]
        (stdout, stderr) = self._runner.run(cmd)
        return [ f for f in stdout.split('\n') if f not in ('', '.', '..') ]


@attr.s
class PTYSingularitySession(SingularitySession):
    """Interactive Singularity Session"""

    @borrowdoc(Session)
    def open(self):
        lgr.debug("Opening TTY connection to singularity container.")
        cmdline = ['singularity', 'shell', 'instance://' + self.name]
        # TODO: Until we work out how the ReproMan session interactive prompt is
        # going to work, we are returning to the OS command prompt when the
        # resource login shell closes. The following line will change after the
        # session management code is developed.
        os.execlp('singularity', *cmdline)

    @borrowdoc(Session)
    def close(self):
        return
