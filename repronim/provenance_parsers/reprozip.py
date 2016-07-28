"""
    Plugin support for provenance YAML files produced by ReproZip utility.

    See: https://vida-nyu.github.io/reprozip/
"""

from repronim.provenance_parser import ProvenanceParser
import yaml

class ReprozipProvenanceParser(ProvenanceParser):

    def __init__(self, source):
        with open(source, 'r') as stream:
            try:
                self.yaml = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def get_distribution(self):
        return {
            'OS': self.yaml['runs'][0]['distribution'][0],
            'version': self.yaml['runs'][0]['distribution'][1]
        }

    def get_environment_vars(self):
        return [(key, self.yaml['runs'][0]['environ'][key]) for key in self.yaml['runs'][0]['environ'].iterkeys()]

    def get_packages(self):
        return [(p['name'], p['version']) for p in self.yaml['packages']]
