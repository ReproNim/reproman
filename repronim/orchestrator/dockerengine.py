# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

from io import BytesIO
from docker import Client
import json

from repronim.orchestrator.base import Orchestrator


class DockerengineOrchestrator(Orchestrator):

    def __init__(self, provenance, kwargs):
        super(DockerengineOrchestrator, self).__init__(provenance)
        self.client = Client(base_url=kwargs['host'])
        self.image_tag = kwargs['image']
        self.container_name = kwargs['image']
        self.dockerfile = ''

    def install_packages(self):
        self.build_dockerfile()
        self.build_image()
        self.run_container()

    def build_dockerfile(self):
        """Create a Dockerfile in memory from provenance info. The Dockerfile will be used to create a Docker image."""

        # Configure base Docker image and maintainer.
        distribution = self.provenance.get_distribution()
        self.dockerfile = 'FROM %s:%s\n' % (distribution['OS'].lower(), distribution['version'])
        self.dockerfile += 'MAINTAINER staff@repronim.org\n'

        # Set up package installs.
        packages = self.provenance.get_packages()
        if packages:
            package_names = [p['name'] for p in packages]
            self.dockerfile += 'RUN apt-get update && apt-get install -y ' + ' '.join(package_names) + '\n'

        # Write CMD to run for container
        command  = self.provenance.get_commandline()
        self.dockerfile += 'CMD ' + ' '.join(command)

    def build_image(self):
        """Use the Dockerfile to build an image."""
        f = BytesIO(self.dockerfile.encode('utf-8'))
        response = [json.loads(line) for line in self.client.build(fileobj=f, rm=True, tag=self.image_tag)]
        if 'error' in response[-1]:
            raise Exception("Docker error - %s" % response[-1]['error'])
            # TODO: Need to figure out how to remove lingering container image from engine.

    def run_container(self):
        """Run a container build from the Docker image created from the provenance file."""
        environment = self.provenance.get_environment_vars()

        container = self.client.create_container(image=self.image_tag, name=self.container_name, environment=environment)
        self.client.start(container)
        # info = self.client.inspect_container(container)
        logs = self.client.logs(container)
        self.lgr.debug(logs)  # Send the call response to the screen.

    def remove_container(self):
        """Remove a container from the Docker engine"""
        self.client.remove_container(self.container_name)

    def remove_image(self):
        """Remove an image fromt he Docker engine"""
        self.client.remove_container(self.image_tag)