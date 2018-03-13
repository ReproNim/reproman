# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Support for Docker distribution(s)."""

import attr
import json
import logging

lgr = logging.getLogger('niceman.distributions.docker')

from .base import Package
from .base import Distribution
from .base import DistributionTracer
from .base import TypedList
from .base import _register_with_representer
from ..dochelpers import borrowdoc
from ..support.exceptions import CommandError


@attr.s(slots=True, frozen=True, cmp=False, hash=True)
class DockerImage(Package):
    """Docker image information"""
    id = attr.ib()
    # Optional
    architecture = attr.ib(default=None)
    operating_system = attr.ib(default=None)
    docker_version = attr.ib(default=None)
    repo_digests = attr.ib(default=None)
    repo_tags = attr.ib(default=None)
    created = attr.ib(default=None)

_register_with_representer(DockerImage)

@attr.s
class DockerDistribution(Distribution):
    """
    Class to provide commands to Docker engine.
    """

    images = TypedList(DockerImage)

    def initiate(self, session):
        """
        Perform any initialization commands needed in the environment
        environment.

        Parameters
        ----------
        session : object
            The Session to work in
        """

        # Raise niceman.support.exceptions.CommandError exception if Docker 
        # engine is not to be found.
        session.execute_command(['docker', 'info'])

    def install_packages(self, session=None):
        """
        Install the Docker images associated to this distribution by the
        provenance into the environment.

        Parameters
        ----------
        session : object
            Session to work in
        """

        for image in self.images:

            # First, look in local Docker engine.
            try:
                session.execute_command(['docker', 'image', 'inspect',
                    image.id])
                continue
            except CommandError:
                pass

            # Then, look in repos.
            found = False
            for digest in image.repo_digests:
                try:
                    session.execute_command(['docker', 'pull', digest])
                    session.execute_command(['docker', 'tag', image.id,
                        image.repo_tags[0]])
                    found = True
                    break
                except CommandError:
                    pass

            # Can't find the image, so complain.
            if not found:
                raise CommandError(cmd='docker pull {}'.format(digest),
                    msg="Unable to locate Docker image {}".format(image.id))

_register_with_representer(DockerDistribution)


class DockerTracer(DistributionTracer):
    """Docker image tracer

    If a Docker engine is not found running in the session, the files
    are quietly passed on to thep next tracer.
    """

    HANDLES_DIRS = False

    @borrowdoc(DistributionTracer)
    def identify_distributions(self, files):
        if not files:
            return

        images = []
        remaining_files = []

        for file in files:
            try:
                image = json.loads(self._session.execute_command(['docker',
                    'image', 'inspect', file])[0])[0]

                # Fail if the Docker image has not been pushed to a repository.
                # If the image is not in a repository, then it can't be
                # expected to be reasonably discovered by others to reproduce.
                if not image['RepoDigests']:
                    raise CommandError(msg='No Docker repos found')

                images.append(DockerImage(
                    id=image['Id'],
                    architecture=image['Architecture'],
                    operating_system=image['Os'],
                    docker_version=image['DockerVersion'],
                    repo_digests=image['RepoDigests'],
                    repo_tags=image['RepoTags'],
                    created=image['Created']
                ))
            except CommandError as exc:
                if exc.stderr.startswith('Cannot connect to the Docker daemon'):
                    lgr.debug("Did not detect Docker engine: %s", exc)
                    return
                if exc.msg == 'No Docker repos found':
                    raise CommandError(cmd="docker image inspect {}".format(
                        file),
                        msg="The Docker image '{}' has not been saved to a \
repository. Please push to a repository before running the trace.".format(
                        file))
                remaining_files.append(file)

        if not images:
            return

        dist = DockerDistribution(
            name="docker",
            images=images
        )

        yield dist, set(remaining_files)

    @borrowdoc(DistributionTracer)
    def _get_packagefields_for_files(self, files):
        return

    @borrowdoc(DistributionTracer)
    def _create_package(self, **package_fields):
        return
