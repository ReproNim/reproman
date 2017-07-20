# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""
Plugin support for TriG formatted RDF provenance files.

See: https://en.wikipedia.org/wiki/TriG_(syntax)
"""

from niceman.formats.base import Provenance
from rdflib import ConjunctiveGraph


class TrigProvenance(Provenance):

    @classmethod
    def _load(cls, source):
        graph = ConjunctiveGraph()
        graph.parse(source, format='trig')
        return graph

    # def get_os(self):
    #     return 'Ubuntu'
    #
    # def get_os_version(self):
    #     return '12.04'
    #
    # def get_create_date(self):
    #     return '20091004T111800Z'
    #
    # def get_environment_vars(self):
    #
    #     results = self.graph.query(
    #         """SELECT DISTINCT ?variable ?value
    #         WHERE {
    #         ?x nipype:environmentVariable ?variable .
    #         ?x prov:value ?value .
    #         }""")
    #
    #     return results

    def get_packages(self):

        results = self._src.query(
            """SELECT DISTINCT ?command ?version
            WHERE {
            ?x nipype:command ?full_command .
            bind( strbefore( $full_command, " " ) as ?command ) .
            ?x nipype:version ?version .
            }""")

        return results

    def get_distributions(self):
        # needs to use get_packages and see what is in there --
        # we might need to come up with a "source_distribution" which
        # would just define packages based on their names without clear
        # definition on how they were obtained
        raise NotImplementedError()

    def get_files(self, limit='all'):
        raise NotImplementedError('TODO')