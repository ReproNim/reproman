# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""
Plugin support for provenance YAML files produced by ReproZip utility.

See: https://vida-nyu.github.io/reprozip/
"""

import yaml

from repronim.dochelpers import exc_str
from .base import Provenance

import logging
lgr = logging.getLogger('repronim.provenance.reprozip')


class ReprozipProvenance(Provenance):
    """Parser for ReproZip provenance (YAML specification) """

    def __init__(self, source):
        self._yaml = None
        self._load(source)

    def _load(self, source):
        with open(source, 'r') as stream:
            try:
                self.yaml = yaml.load(stream)
            except yaml.YAMLError as exc:
                lgr.error("Failed to load %s: %s", source, exc_str(exc))
                raise  # TODO -- we might want a dedicated exception here

    def get_os(self):
        return self.yaml['runs'][0]['distribution'][0]

    def get_os_version(self):
        return self.yaml['runs'][0]['distribution'][1]

    def get_create_date(self):
        format = '%Y%m%dT%H%M%SZ'
        return self.yaml['runs'][0]['date'].strftime(format)

    def get_environment_vars(self):
        return self.yaml['runs'][0]['environ']

    def get_packages(self):
        return [{'name': p['name'], 'version': p['version']} for p in self.yaml['packages']]

    def get_commandline(self):
        return self.yaml['runs'][0]['argv']
