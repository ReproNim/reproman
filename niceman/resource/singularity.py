# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of a Singularity environment."""

import attr
import os
import six
from ..cmd import Runner
from ..dochelpers import borrowdoc
from ..support.exceptions import CommandError
from .session import POSIXSession, Session
from .base import Resource
from ..utils import attrib

import logging
lgr = logging.getLogger('niceman.resource.singularity')


@attr.s
class Singularity(Resource):
    """
    Environment manager which manages a Singularity container.
    """

    # Generic properties of any Resource
    name = attrib()

    # Container properties
    id = attrib()
    image = attrib(doc="Base image filename or url")
    type = attrib(default='singularity')

    status = attrib()
    _runner = attrib()

    def connect(self):
        """
        Open a connection to the environment.
        """
        self._runner = Runner()

        # Make sure singularity is installed
        stdout, _ = self._runner.run(['singularity', '--version'])
        if stdout.startswith('2.2') or stdout.startswith('2.3'):
            # Running singularity instances and managing them didn't happen
            # until version 2.4. See: https://singularity.lbl.gov/archive/
            raise CommandError(msg="Singularity version >= 2.4 required.")

        # Get instance info if we have one running.
        info = self.get_instance_info()
        if info:
            if not self.name:
                self.name = info['name']
            if not self.id:
                # Daemon names for a singularity instance are unique so they
                # can do double duty as the ID. While not a global ID, it
                # will do the trick locally.
                self.id = info['name']
            self.image = info['image']
            self.status = 'running'
        else:
            self.id = None
            self.status = None

    def create(self):
        """
        Create a container instance.

        Returns
        -------
        dict : config parameters to capture in the inventory file
        """
        # Check to see if the container is already running.
        if self.get_instance_info():
            lgr.info('Resource {} already exists.'.format(self.name))
        else:
            # Start the container instance.
            # NOTE: Logging stdout and stderr hangs the run call, so we
            # disable the logging in the run call below.
            self._runner.run(['singularity', 'instance.start', self.image,
                self.name], log_stdout=False, log_stderr=False)

        # Update status
        self.id = self.name
        self.status = 'running'
        return {
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
        self._runner.run(['singularity', 'instance.stop', self.name])

        # Update status
        self.id = None
        self.status = None

    def start(self):
        """
        Start a stopped container.
        """
        lgr.info("Singularity does not provide a start feature.")

    def stop(self):
        """
        Stop a running container.
        """
        lgr.info("Singularity does not provide a stop feature.")

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
        dict : instance info
        """
        try:
            stdout, _ = self._runner.run(['singularity', 'instance.list'])
        except CommandError:
            return None

        # Parse stdout to find the running instance.
        # The output of instance.list is a table with columns:
        #   DAEMON NAME, PID, and CONTAINER IMAGE
        # Daemon names are unique on each server.
        for row in stdout.splitlines()[1:]:
            items = row.split()
            if self.name == items[0] or self.id == items[0]:
                return {
                    'name': items[0],  # daemon name
                    'pid': items[1],   # daemon process id
                    'image': items[2]  # container image file
                }


@attr.s
class SingularitySession(POSIXSession):
    name = attrib(default=attr.NOTHING)
    _runner = Runner()

    @borrowdoc(Session)
    def _execute_command(self, command, env=None, cwd=None):
        if env:
            raise NotImplementedError("passing env variables to session execution")
        if cwd:
            raise NotImplementedError("handle cwd for singularity")
        lgr.debug('Running command %r', command)
        # If command is a string, convert it to a list
        if isinstance(command, six.string_types):
            command = command.split()
        stdout, stderr = self._runner.run(
            ['singularity', 'exec', 'instance://' + self.name] + command,
            expect_fail=True)

        return (stdout, stderr)

    @borrowdoc(Session)
    def put(self, src_path, dest_path, uid=-1, gid=-1):
        dest_dir, _ = os.path.split(dest_path)
        self.mkdir(dest_dir, parents=True)
        cmd = 'cat {} | singularity exec instance://{} tee {} > /dev/null'
        self._runner.run(cmd.format(src_path, self.name, dest_path))

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid)

    @borrowdoc(Session)
    def get(self, src_path, dest_path, uid=-1, gid=-1):
        dest_dir, _ = os.path.split(dest_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        cmd = 'singularity exec instance://{} cat {} > {}'
        self._runner.run(cmd.format(self.name, src_path, dest_path))

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid, remote=False)


@attr.s
class PTYSingularitySession(SingularitySession):
    """Interactive Singularity Session"""

    @borrowdoc(Session)
    def open(self):
        lgr.debug("Opening TTY connection to singularity container.")
        cmdline = ['singularity', 'shell', 'instance://' + self.name]
        # TODO: Until we work out how the Niceman session interactive prompt is
        # going to work, we are returning to the OS command prompt when the
        # resource login shell closes. The following line will change after the
        # session management code is developed.
        os.execlp('singularity', *cmdline)

    @borrowdoc(Session)
    def close(self):
        return
