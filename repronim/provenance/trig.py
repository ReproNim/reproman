# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""
Plugin support for TriG formatted RDF provenance files.

See: https://en.wikipedia.org/wiki/TriG_(syntax)
"""

from repronim.provenance.base import Provenance
from rdflib import ConjunctiveGraph

class TrigProvenance(Provenance):

    def __init__(self, source):
        self.graph = ConjunctiveGraph()
        self.graph.parse(source, format='trig')

    def get_os(self):
        return 'Ubuntu'

    def get_os_version(self):
        return '12.04'

    def get_create_date(self):
        return '20091004T111800Z'

    def get_environment_vars(self):

        results = self.graph.query(
            """SELECT DISTINCT ?variable ?value
            WHERE {
            ?x nipype:environmentVariable ?variable .
            ?x prov:value ?value .
            }""")

        return results

    def get_packages(self):

        results = self.graph.query(
            """SELECT DISTINCT ?command ?version
            WHERE {
            ?x nipype:command ?full_command .
            bind( strbefore( $full_command, " " ) as ?command ) .
            ?x nipype:version ?version .
            }""")

        return results
