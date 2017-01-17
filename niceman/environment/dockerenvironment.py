# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Environment sub-class to provide management of environment engine."""

from io import BytesIO
from ..support.exceptions import CommandError

from niceman.environment.base import Environment


class DockerEnvironment(Environment):
    """
    Environment manager which talks to a Docker engine.
    """

    def __init__(self, config = {}):
        """
        Class constructor

        Parameters
        ----------
        config : dictionary
            Configuration parameters for the environment.
        """
        if not 'base_image_id' in config:
            config['base_image_id'] = 'ubuntu:latest'
        if not 'stdin_open' in config:
            config['stdin_open'] = True

        super(DockerEnvironment, self).__init__(config)

        self._client = None
        self._image = None
        self._container = None

        # Open a client connection to the Docker engine.
        docker_client = self.get_resource_client()
        self._client = docker_client()

    def create(self, name, image_id):
        """
        Create a baseline Docker image and run it to create the container.

        Parameters
        ----------
        name : string
            Name identifier of the environment to be created.
        image_id : string
            Identifier of the image to use when creating the environment.
        """
        if name:
            self['name'] = name
        if image_id:
            self['base_image_id'] = image_id

        dockerfile = self._get_base_image_dockerfile(self['base_image_id'])
        self._build_image(dockerfile)
        self._run_container()

    def connect(self, name):
        """
        Open a connection to the environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to connect to.
        """

        # Following call may raise these exceptions:
        #    docker.errors.NotFound - If the container does not exist.
        #    docker.errors.APIError - If the server returns an error.
        self._container = self._client.containers.get(name)

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
        for i, line in enumerate(self._container.exec_run(cmd=command, stream=True)):
            if line.startswith('rpc error'):
                raise CommandError(cmd=command, msg="Docker error - %s" % line)
            self._lgr.debug("exec#%i: %s", i, line.rstrip())

    def _get_base_image_dockerfile(self, base_image_id):
        """
        Creates the Dockerfile needed to create the baseline Docker image.

        Parameters
        ----------
        base_image_id : string
            "repo:tag" of Docker image to use as base image.

        Returns
        -------
        string
            String containing the Dockerfile commands.
        """
        dockerfile = 'FROM %s\n' % (base_image_id,)
        dockerfile += 'MAINTAINER staff@niceman.org\n'
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
            tag="niceman:{}".format(self['name']), rm=True)

    def _run_container(self):
        """
        Start the Docker container from the image.
        """
        # The following call may throw the following exceptions:
        #    docker.errors.EnvironmentError - If the container exits with a non-zero
        #        exit code and detach is False.
        #    docker.errors.ImageNotFound - If the specified image does not exist.
        #    docker.errors.APIError - If the server returns an error.
        self._container = self._client.containers.run(image=self._image,
            stdin_open=self['stdin_open'], detach=True,
            name=self['name'])

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