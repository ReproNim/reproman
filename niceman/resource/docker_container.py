# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of environment engine."""

import attr
import docker
import dockerpty
import json
from niceman import utils
from ..support.exceptions import CommandError, ResourceError
from .base import Resource, attrib

import logging
lgr = logging.getLogger('niceman.resource.docker_container')


@attr.s
class DockerContainer(Resource):
    """
    Environment manager which manages a Docker container.
    """

    # Container properties
    name = attr.ib()
    id = attr.ib(default=None)
    type = attr.ib(default='docker-container')

    base_image_id = attrib(default='ubuntu:latest',
        doc="Docker base image ID from which to create the running instance")
    engine_url = attrib(default='unix:///var/run/docker.sock',
        doc="Docker server URL where engine is listening for connections")

    status = attr.ib(default=None)

    # Docker client and container objects.
    _client = attr.ib(default=None)
    _container = attr.ib(default=None)

    def connect(self):
        """
        Open a connection to the environment.
        """
        # Open a client connection to the Docker engine.
        self._client = docker.Client(base_url=self.engine_url)

        containers = []
        for container in self._client.containers(all=True):
            assert self.id or self.name, "Name or id must be known"
            if self.id and not container.get('Id').startswith(self.id):
                lgr.log(5, "Container %s does not match by id: %s", container,
                        self.id)
                continue
            if self.name and ('/' + self.name) not in container.get('Names'):
                lgr.log(5, "Container %s does not match by name: %s", container,
                        self.name)
                continue
            # TODO: make above more robust and centralize across different resources/backends?
            containers.append(container)
        if len(containers) == 1:
            self._container = containers[0]
            self.id = self._container.get('Id')
            self.status = self._container.get('State')
        elif len(containers) > 1:
            raise ResourceError(
                "Multiple container matches found: %s" % str(containers)
            )
        else:
            self.id = None
            self.status = None

    def create(self):
        """
        Create a baseline Docker image and run it to create the container.

        Returns
        -------
        dict : config parameters to capture in the inventory file
        """
        if self._container:
            raise ResourceError(
                "Container '{}' (ID {}) already exists in Docker".format(
                    self.name, self.id))
        # image might be of the form repository:tag -- pull would split them
        # if needed
        for line in self._client.pull(repository=self.base_image_id, stream=True):
            status = json.loads(utils.to_unicode(line, "utf-8"))
            output = status['status']
            if 'progress' in status:
                output += ' ' + status['progress']
            lgr.info(output)
        self._container = self._client.create_container(
            name=self.name,
            image=self.base_image_id,
            stdin_open=True,
            tty=True,
            command='/bin/bash',
        )
        self.id = self._container.get('Id')
        self._client.start(container=self.id)
        self.status = 'running'
        return {
            'id': self.id,
            'status': self.status
        }

    def delete(self):
        """
        Deletes a container from the Docker engine.
        """
        if self._container:
            self._client.remove_container(self._container, force=True)

    def start(self):
        """
        Starts a container in the Docker engine.
        """
        if self._container:
            self._client.start(container=self._container.get('Id'))

    def stop(self):
        """
        Stops a container in the Docker engine.
        """
        if self._container:
            self._client.stop(container=self._container.get('Id'))

    def get_session(self, pty=False, shared=None):
        """
        Log into a container and get the command line
        """
        if not self._container:
            self.connect()

        if pty and shared is not None and not shared:
            lgr.warning("Cannot do non-shared pty session for docker yet")
        return (PTYDockerSession if pty else DockerSession)(
            client=self._client,
            container=self._container
        )


from niceman.resource.session import POSIXSession


@attr.s
class DockerSession(POSIXSession):
    client = attr.ib()
    container = attr.ib()

    def _execute_command(self, command, env=None, cwd=None):
        """
        Execute the given command in the container.

        Parameters
        ----------
        command : string or list
            Shell command to send to the container to execute. The command can
            be a string or a list of tokens that create the command.
        env : dict
            Complete environment to be used

        Returns
        -------
        out, err
        """
        #command_env = self.get_updated_env(env)
        if env:
            raise NotImplementedError("passing env variables to docker session execution")

        if cwd:
            raise NotImplementedError("handle cwd for docker")
        # if command_env:
            # TODO: might not work - not tested it
            # command = ['export %s=%s' % k for k in command_env.items()] + command

        # The following call may throw the following exception:
        #    docker.errors.APIError - If the server returns an error.
        lgr.debug('Running command %r', command)
        execute = self.client.exec_create(container=self.container, cmd=command)
        out = ''
        for i, line in enumerate(
                self.client.exec_start(exec_id=execute['Id'],
                stream=True)
        ):
            if line.startswith(b'rpc error'):
                raise CommandError(cmd=command, msg="Docker error - %s" % line)
            out += utils.to_unicode(line, "utf-8")
            lgr.debug("exec#%i: %s", i, line.rstrip())
        return (out, self.client.exec_inspect(execute['Id'])['ExitCode'])

    # XXX should we start/stop on open/close or just assume that it is running already?


    def put(self, src_path, dest_path, preserve_perms=False,
                owner=None, group=None, recursive=False):
        """Take file on the local file system and copy over into the session
        """
        # self.ssh.put([src_path], remotepath=dest_path)
        pass

    def get(self, src_path, dest_path, preserve_perms=False,
                  owner=None, group=None, recursive=False):
        """Retrieve a file from the remote system
        """
        # self.ssh.get(src_path, localpath=dest_path)
        pass


@attr.s
class PTYDockerSession(DockerSession):
    """Interactive Docker Session"""

    def open(self):
        lgr.debug("Opening TTY connection to docker container.")
        # TODO: probably call to super to assure that we have it running?
        dockerpty.start(self.client, self.container, logs=0)

    def close(self):
        # XXX ?
        pass

    # XXX should we overload execute_command?