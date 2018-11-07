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
import io
import json
import os
import requests
import tarfile
from niceman import utils
from ..cmd import Runner
from ..support.exceptions import CommandError, ResourceError
from niceman.dochelpers import borrowdoc
from niceman.resource.session import POSIXSession, Session
from .base import Resource
from ..utils import attrib

import logging
lgr = logging.getLogger('niceman.resource.docker_container')


@attr.s
class DockerContainer(Resource):
    """
    Environment manager which manages a Docker container.
    """

    # Generic properties of any Resource
    name = attrib(default=attr.NOTHING)

    # Container properties
    id = attrib()
    type = attrib(default='docker-container')

    image = attrib(default='ubuntu:latest',
        doc="Docker base image ID from which to create the running instance")
    engine_url = attrib(default='unix:///var/run/docker.sock',
        doc="Docker server URL where engine is listening for connections")
    seccomp_unconfined = attrib(default=False,
        doc="Disable kernel secure computing mode when creating the container")

    status = attrib()

    # Docker client and container objects.
    _client = attrib()
    _container = attrib()

    @staticmethod
    def is_engine_running(base_url=None):
        """Check the local environment to see if the Docker engine is running.

        Parameters
        ----------
        base_url : str
            URL or socket where Docker engine is listening

        Returns
        -------
        boolean
        """
        try:
            session = docker.Client(base_url=base_url)
            session.info()
        except (requests.exceptions.ConnectionError,
                docker.errors.DockerException):
            return False
        return True

    @staticmethod
    def is_container_running(container_name):
        """Ping the local environment to see if given container is running.

        Parameters
        ----------
        container_name : string

        Returns
        -------
        boolean
        """
        stdout, _ = Runner().run(['docker', 'ps', '--quiet', '--filter',
            'name=^/{}$'.format(container_name)])
        if stdout.strip():
            return True
        return False

    def connect(self):
        """
        Open a connection to the environment.
        """
        # Open a client connection to the Docker engine.
        self._client = docker.Client(base_url=self.engine_url)

        containers = []
        for container in self._client.containers(all=True):
            assert self.id or self.name,\
                "Container name or id must be known"
            if self.id and not container.get('Id').startswith(self.id):
                lgr.log(5, "Container %s does not match by id: %s", container,
                        self.id)
                continue
            if self.name and ('/' + self.name) \
                    not in container.get('Names'):
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
        for line in self._client.pull(repository=self.image, stream=True):
            status = json.loads(utils.to_unicode(line, "utf-8"))
            output = status['status']
            if 'progress' in status:
                output += ' ' + status['progress']
            lgr.info(output)
        args = {
            'name': self.name,
            'image': self.image,
            'stdin_open': True,
            'tty': True,
            'command': '/bin/bash'
        }
        # When running the rztracer binary in a Docker container, it is
        # necessary to suspend the kernel's security facility when creating
        # the container. Since it is a security issue, the default is to
        # *not* turn it off.
        if self.seccomp_unconfined:
            args['host_config'] = {
                'SecurityOpt': ['seccomp:unconfined']
            }
        self._container = self._client.create_container(**args)
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


@attr.s
class DockerSession(POSIXSession):
    client = attrib(default=attr.NOTHING)
    container = attrib(default=attr.NOTHING)

    @borrowdoc(Session)
    def _execute_command(self, command, env=None, cwd=None):
        #command_env = self.get_updated_env(env)
        if env:
            raise NotImplementedError("passing env variables to docker session execution")

        if cwd:
            # TODO: implement
            # raise NotImplementedError("handle cwd for docker")
            lgr.warning("cwd is not handled in docker yet")
            pass
        # if command_env:
            # TODO: might not work - not tested it
            # command = ['export %s=%s' % k for k in command_env.items()] + command

        # The following call may throw the following exception:
        #    docker.errors.APIError - If the server returns an error.
        lgr.debug('Running command %r', command)
        out = []
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

        exit_code = self.client.exec_inspect(execute['Id'])['ExitCode']
        if exit_code not in [0, None]:
            msg = "Failed to run %r. Exit code=%d. out=%s err=%s" \
                % (command, exit_code, out, out)
            raise CommandError(str(command), msg, exit_code, '', out)
        else:
            lgr.log(8, "Finished running %r with status %s", command,
                exit_code)

        return (out, '')

    # XXX should we start/stop on open/close or just assume that it is running already?


    @borrowdoc(Session)
    def put(self, src_path, dest_path, uid=-1, gid=-1):
        # To copy one or more files to the container, the API recommends
        # to do so with a tar archive. http://docker-py.readthedocs.io/en/1.5.0/api/#copy
        dest_path = self._prepare_dest_path(src_path, dest_path,
                                            local=False, absolute_only=True)
        dest_dir, dest_basename = os.path.split(dest_path)
        tar_stream = io.BytesIO()
        tar_file = tarfile.TarFile(fileobj=tar_stream, mode='w')
        tar_file.add(src_path, arcname=dest_basename)
        tar_file.close()
        tar_stream.seek(0)
        self.client.put_archive(container=self.container['Id'], path=dest_dir,
            data=tar_stream)

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid)

    @borrowdoc(Session)
    def get(self, src_path, dest_path=None, uid=-1, gid=-1):
        src_dir, src_basename = os.path.split(src_path)
        dest_path = self._prepare_dest_path(src_path, dest_path)
        dest_dir = os.path.dirname(dest_path)
        stream, stat = self.client.get_archive(self.container, src_path)
        tarball = tarfile.open(fileobj=io.BytesIO(stream.read()))
        tarball.extractall(path=dest_dir)
        os.rename(os.path.join(dest_dir, src_basename), dest_path)

        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid, remote=False)


@attr.s
class PTYDockerSession(DockerSession):
    """Interactive Docker Session"""

    @borrowdoc(Session)
    def open(self):
        lgr.debug("Opening TTY connection to docker container.")
        # TODO: probably call to super to assure that we have it running?
        dockerpty.start(self.client, self.container, logs=0)

    @borrowdoc(Session)
    def close(self):
        # XXX ?
        pass

    # XXX should we overload execute_command?