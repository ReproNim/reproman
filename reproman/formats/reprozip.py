# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""
Plugin support for provenance YAML files produced by ReproZip utility.

See: https://vida-nyu.github.io/reprozip/
"""

import io
import yaml

from .base import Provenance

import logging
lgr = logging.getLogger('niceman.formats.reprozip')


class ReprozipProvenance(Provenance):
    """Parser for ReproZip file format (YAML specification) """

    @classmethod
    def _load(cls, source):
        with io.open(source, encoding='utf-8') as stream:
            config = yaml.safe_load(stream)
            # TODO: Check version of ReproZip file and warn if unknown
            return config

    # Might come handy to define 'base' whenever we get there
    # def get_os(self):
    #     return self.yaml['runs'][0]['distribution'][0]
    #
    # def get_os_version(self):
    #     return self.yaml['runs'][0]['distribution'][1]
    #
    # def get_create_date(self):
    #     format = '%Y%m%dT%H%M%SZ'
    #     return self.yaml['runs'][0]['date'].strftime(format)
    #
    # def get_environment_vars(self):
    #     return self.yaml['runs'][0]['environ']
    #
    # def get_packages(self):
    #     return [{'name': p['name'], 'version': p['version']} for p in self.yaml['packages']]
    #
    # def get_commandline(self):
    #     return self.yaml['runs'][0]['argv']

    def get_files(self, limit='all'):
        """Pulls the system files from a ReproZip configuration into a set
    
        Given a ReproZip configuration (read into a dictionary) it pulls
        the list of files from "packages" and "other files" sections into a
        set. It excludes files from "input_output".
    
        Parameters
        ----------
        config : dict
            ReproZip configuration
        other_files : bool, optional
            Either to return also other_files
    
        Return
        ------
        set
            Files listed in the configuration
        """

        files = set()

        src_yaml = self._src
        if limit in {'all', 'packaged'}:
            for package in src_yaml.get('packages', []) or []:
                if 'files' in package:
                    files.update(package.get('files', []))

        if limit in {'all', 'loose'} and 'other_files' in src_yaml:
            files.update(src_yaml.get("other_files", []))

        return files
