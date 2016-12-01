# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Container sub-class to provide management of container engine."""

from io import BytesIO
import docker
import json

from repronim.container.base import Container


class DockercontainerContainer(Container):
    """
    Container manager which talks to a Docker engine.
    """

    def __init__(self, resource, config = {}):
        """
        Class constructor

        Parameters
        ----------
        resource : object
            Resource sub-class instance
        config : dictionary
            Configuration parameters for the container.
        """

        self._image_id = None
        self._container_id = None

        super(DockercontainerContainer, self).__init__(resource, config)

        if not self.get_config('base_image_tag'):
            self.set_config('base_image_tag', 'ubuntu:latest')
        if not self.get_config('engine_url'):
            self.set_config('engine_url', 'unix:///var/run/docker.sock')
        if not self.get_config('stdin_open'):
            self.set_config('stdin_open', True)

        # Initialize the client connection to Docker engine.
        self._client = docker.Client(self.get_config('engine_url'))

    def create(self):
        """
        Create a baseline Docker image and run it to create the container.
        """
        dockerfile = self._get_base_image_dockerfile(self.get_config('base_image_tag'))
        self._build_image(dockerfile)
        self._run_container()

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

        Returns
        -------
        list
            List of STDOUT lines from the container.
        """

        command_env = self.get_updated_env(env)

        if command_env:
            # TODO: might not work - not tested it
            command = ['export %s=%s;' % k for k in command_env.items()] + command
        execute = self._client.exec_create(container=self._container_id, cmd=command)
        response = [line for line in self._client.exec_start(exec_id=execute['Id'], stream=True)]
        return response

    def _get_base_image_dockerfile(self, base_image_tag):
        """
        Creates the Dockerfile needed to create the baseline Docker image.

        Parameters
        ----------
        base_image_tag : string
            "repo:tag" of Docker image to use as base image.

        Returns
        -------
        string
            String containing the Dockerfile commands.
        """
        dockerfile = 'FROM %s\n' % (base_image_tag,)
        dockerfile += 'MAINTAINER staff@repronim.org\n'
        return dockerfile

    def _build_image(self, dockerfile):
        """
        Create the Docker image in the Docker engine.

        Parameters
        ----------
        dockerfile : string
            The contents of the Dockerfile used to create the contaner.
        """
        f = BytesIO(dockerfile.encode('utf-8'))
        response = [json.loads(line) for line in self._client.build(fileobj=f, rm=True)]
        self._lgr.debug(response)
        if 'error' in response[-1]:
            raise Exception("Docker error - %s" % response[-1]['error'])
            # TODO: Need to figure out how to remove lingering container image from engine.

        # Retrieve image_id from last result string which is in the
        # form of: u'Successfully built 73ccd6b8d194\n'
        self._image_id = response[-1]['stream'].split(' ')[2][:-1]

    def _run_container(self):
        """
        Start the Docker container from the image.
        """
        container = self._client.create_container(image=self._image_id,
            stdin_open=self.get_config('stdin_open'))
        self._client.start(container)
        self._lgr.debug(self._client.logs(container))
        self._container_id = container['Id']

    def remove_container(self):
        """
        Deletes a container from the Docker engine.
        """
        self._client.remove_container(self._container_id)

    def remove_image(self):
        """
        Deletes an image from the Docker engine.
        """
        self._client.remove_container(self._image_id)