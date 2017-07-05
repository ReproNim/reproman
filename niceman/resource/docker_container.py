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
from ..support.exceptions import CommandError, ResourceError
from .base import Resource

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

    base_image_id = attr.ib(default='ubuntu:latest')
    engine_url = attr.ib(default='unix:///var/run/docker.sock')

    status = attr.ib(default=None)

    # Management properties
    _client = attr.ib(default=None)
    _container = attr.ib(default=None)

    @staticmethod
    def get_backend_properties():
        """
        Return the config properties specific to this resource type.

        Returns
        -------
        dict : key = resource property, value = property
        """
        return {
            'base_image_id': 'Docker base image ID from which to create the running instance',
            'engine_url': 'Docker server URL where engine is listening for connections',
        }

    def connect(self):
        """
        Open a connection to the environment.
        """
        # Open a client connection to the Docker engine.
        self._client = docker.Client(base_url=self.engine_url)

        containers = []
        for container in self._client.containers(all=True):
            if self.id == container.get('Id') or '/' + self.name == container.get('Names')[0]:
                containers.append(container)

        if len(containers) == 1:
            self._container = containers[0]
            self.id = self._container.get('Id')
            self.status = self._container.get('State')
        elif len(containers) > 1:
            raise ResourceError("Multiple container matches found")
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
            status = json.loads(line)
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
        self.status = 'running'
        self._client.start(container=self.id)
        return {
            'id': self.id,
            'status': self.status
        }

    def execute_command(self, command, env=None):
        """
        Execute the given command in the container.

        Parameters
        ----------
        command : string or list
            Shell command to send to the container to execute. The command can
            be a string or a list of tokens that create the command.
        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call
        """

        command_env = self.get_updated_env(env)

        # if command_env:
            # TODO: might not work - not tested it
            # command = ['export %s=%s' % k for k in command_env.items()] + command

        # The following call may throw the following exception:
        #    docker.errors.APIError - If the server returns an error.
        execute = self._client.exec_create(container=self._container, cmd=command)
        for i, line in enumerate(self._client.exec_start(exec_id=execute['Id'], stream=True)):
            if line.startswith('rpc error'):
                raise CommandError(cmd=command, msg="Docker error - %s" % line)
            lgr.debug("exec#%i: %s", i, line.rstrip())

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

    def login(self):
        """
        Log into a container and get the command line
        """
        lgr.debug("Opening TTY connection to docker container.")
        dockerpty.start(self._client, self._container, logs=0)