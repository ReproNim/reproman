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

        self._image = None
        self._container = None

        super(DockercontainerContainer, self).__init__(resource, config)

        if not self.get_config('base_image_tag'):
            self.set_config('base_image_tag', 'ubuntu:latest')
        if not self.get_config('engine_url'):
            self.set_config('engine_url', 'unix:///var/run/docker.sock')
        if not self.get_config('stdin_open'):
            self.set_config('stdin_open', True)

        # Initialize the client connection to Docker engine.
        self._client = docker.DockerClient(self.get_config('engine_url'))

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
        """

        command_env = self.get_updated_env(env)

        if command_env:
            # TODO: might not work - not tested it
            command = ['export %s=%s;' % k for k in command_env.items()] + command

        # The following call may throw the following exception:
        #    docker.errors.APIError - If the server returns an error.
        for i, line in enumerate(self._container.exec_run(cmd=command, stream=True)):
            if line.startswith('rpc error'):
                raise Exception("Docker error - %s" % line)
            self._lgr.debug("exec#%i: %s", i, line.rstrip())

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
        # The following call may throw the following exceptions:
        #    docker.errors.BuildError - If there is an error during the build.
        #    docker.errors.APIError - If the server returns any other error.
        self._image = self._client.images.build(fileobj=f,
            tag="repronim:%s" % self.get_config('resource_id'), rm=True)

    def _run_container(self):
        """
        Start the Docker container from the image.
        """
        # The following call may throw the following exceptions:
        #    docker.errors.ContainerError - If the container exits with a non-zero
        #        exit code and detach is False.
        #    docker.errors.ImageNotFound - If the specified image does not exist.
        #    docker.errors.APIError - If the server returns an error.
        self._container = self._client.containers.run(image=self._image,
            stdin_open=self.get_config('stdin_open'), detach=True)

    def remove_container(self):
        """
        Deletes a container from the Docker engine.
        """
        self._container.remove(force=True)

    def remove_image(self):
        """
        Deletes an image from the Docker engine.
        """
        self._client.images.remove(self._image)