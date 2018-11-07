# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Support for Singularity distribution(s)."""

import attr
import json
import logging
import os
import tempfile
import uuid


lgr = logging.getLogger('niceman.distributions.singularity')

from .base import Package
from .base import Distribution
from .base import DistributionTracer
from .base import TypedList
from .base import _register_with_representer
from ..dochelpers import borrowdoc, exc_str
from ..utils import attrib, md5sum, chpwd


@attr.s(slots=True, frozen=True, cmp=False, hash=True)
class SingularityImage(Package):
    """Singularity image information"""
    md5 = attrib(default=attr.NOTHING)
    # Optional
    bootstrap = attrib()
    maintainer = attrib()
    deffile = attrib()
    schema_version = attrib()
    build_date = attrib()
    build_size = attrib()
    singularity_version = attrib()
    base_image = attrib()
    mirror_url = attrib()
    url = attrib()
    path = attrib()


_register_with_representer(SingularityImage)


@attr.s
class SingularityDistribution(Distribution):
    """
    Class to provide commands to Singularity.
    """

    images = TypedList(SingularityImage)

    def initiate(self, session):
        """
        Perform any initialization commands needed in the environment.

        Parameters
        ----------
        session : object
            The Session to work in
        """

        # Raise niceman.support.exceptions.CommandError exception if
        # Singularity is not to be found.
        session.execute_command(['singularity', 'selftest'])

    def install_packages(self, session):
        """
        Install the Singularity images associated to this distribution by the
        provenance into the environment.

        Parameters
        ----------
        session : object
            Session to work in
        """

        # TODO: Currently we have no way to locate the image given the metadata


_register_with_representer(SingularityDistribution)


class SingularityTracer(DistributionTracer):
    """Singularity image tracer

    If a given file is not identified as a singularity image, the files
    are quietly passed on to the next tracer.
    """

    HANDLES_DIRS = False

    @borrowdoc(DistributionTracer)
    def identify_distributions(self, files):
        if not files:
            return

        images = []
        remaining_files = set()
        url = None
        path = None

        for file_path in files:
            try:
                if file_path.startswith('shub:/'):
                    # Correct file path for path normalization in retrace.py
                    if not file_path.startswith('shub://'):
                        file_path = file_path.replace('shub:/', 'shub://')
                    temp_path = "{}.simg".format(uuid.uuid4())
                    with chpwd(tempfile.gettempdir()):
                        msg = "Downloading Singularity image {} for tracing"
                        lgr.info(msg.format(file_path))
                        self._session.execute_command(['singularity', 'pull',
                            '--name', temp_path, file_path])
                        image = json.loads(self._session.execute_command(
                            ['singularity', 'inspect', temp_path])[0])
                        url = file_path
                        md5 = md5sum(temp_path)
                        os.remove(temp_path)
                else:
                    path = os.path.abspath(file_path)
                    image = json.loads(self._session.execute_command(
                        ['singularity', 'inspect', file_path])[0])
                    md5 = md5sum(file_path)

                images.append(SingularityImage(
                    md5=md5,
                    bootstrap=image.get(
                        'org.label-schema.usage.singularity.deffile.bootstrap'),
                    maintainer=image.get('MAINTAINER'),
                    deffile=image.get(
                        'org.label-schema.usage.singularity.deffile'),
                    schema_version=image.get('org.label-schema.schema-version'),
                    build_date=image.get('org.label-schema.build-date'),
                    build_size=image.get('org.label-schema.build-size'),
                    singularity_version=image.get(
                        'org.label-schema.usage.singularity.version'),
                    base_image=image.get(
                        'org.label-schema.usage.singularity.deffile.from'),
                    mirror_url=image.get(
                        'org.label-schema.usage.singularity.deffile.mirrorurl'),
                    url=url,
                    path=path
                ))
            except Exception as exc:
                lgr.debug("Probably %s is not a Singularity image: %s",
                    file_path, exc_str(exc))
                lgr.debug(exc)
                remaining_files.add(file_path)

        if not images:
            return

        dist = SingularityDistribution(
            name="singularity",
            images=images
        )

        yield dist, remaining_files

    @borrowdoc(DistributionTracer)
    def _get_packagefields_for_files(self, files):
        return

    @borrowdoc(DistributionTracer)
    def _create_package(self, **package_fields):
        return
