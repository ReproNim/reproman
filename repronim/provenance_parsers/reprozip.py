"""
    Plugin support for provenance YAML files produced by ReproZip utility.

    See: https://vida-nyu.github.io/reprozip/
"""

from repronim.dochelpers import exc_str
from repronim.provenance_parser import ProvenanceParser
import yaml

import logging
lgr = logging.getLogger('repronim.prov.parsers.reprozip')


class ReprozipProvenanceParser(ProvenanceParser):
    """Parser for ReproZip provenance (YAML specification) """

    _supports_chaining = False

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

    def get_distribution(self):
        return {
            'OS': self.yaml['runs'][0]['distribution'][0],
            'version': self.yaml['runs'][0]['distribution'][1]
        }

    def get_create_date(self):
        format = '%Y%m%dT%H%M%SZ'
        return self.yaml['runs'][0]['date'].strftime(format)

    def get_environment_vars(self):
        return [(key, self.yaml['runs'][0]['environ'][key]) for key in self.yaml['runs'][0]['environ'].iterkeys()]

    def get_packages(self):
        return [(p['name'], p['version']) for p in self.yaml['packages']]
