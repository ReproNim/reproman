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
from ..utils import attrib


@attr.s(slots=True, frozen=True, cmp=False, hash=True)
class DockerImage(Package):
    """Docker image information"""
    id = attrib(default=attr.NOTHING)
    # Optional
    architecture = attrib()
    operating_system = attrib()
    docker_version = attrib()
    repo_digests = attrib()
    repo_tags = attrib()
    created = attrib()

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

    def install_packages(self, session):
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
    are quietly passed on to the next tracer.
    """

    HANDLES_DIRS = False

    @borrowdoc(DistributionTracer)
    def identify_distributions(self, files):
        if not files:
            return

        # Punt if Docker daemon to found
        if self._session.execute_command('ps -e')[0].find('dockerd') == -1:
            return

        images = []
        remaining_files = set()

        for file in files:
            try:
                image = json.loads(self._session.execute_command(['docker',
                    'image', 'inspect', file])[0])[0]

                # Warn user if the image does not have any RepoDigest entries.
                if not image['RepoDigests']:
                    lgr.warning("The Docker image '%s' does not have any "
                        "repository IDs associated with it", file)

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
                remaining_files.add(file)
            except Exception as exc:
                lgr.debug(exc)
                remaining_files.add(file)

        if not images:
            return

        dist = DockerDistribution(
            name="docker",
            images=images
        )

        yield dist, remaining_files

    @borrowdoc(DistributionTracer)
    def _get_packagefields_for_files(self, files):
        return

    @borrowdoc(DistributionTracer)
    def _create_package(self, **package_fields):
        return
