# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Parsers of provenance information"""

from importlib import import_module
import abc

from ..utils import file_basename
from ..dochelpers import exc_str
from ..support.exceptions import SpecLoadingError

_known_formats = ['reprozip', 'repronim', 'trig']
_known_extensions = {
    'yml': ['repronim', 'reprozip'],
    'trig': ['trig']
}

import logging
lgr = logging.getLogger('repronim.prov')


class Provenance(object):
    """
    Base class to handle the collection and management of provenance information.
    """

    __metaclass__ = abc.ABCMeta

    @staticmethod
    def factory(source, format='repronimspec'):
        """
        Factory method for creating the appropriate Provenance sub-class based
        on format type.

        Parameters
        ----------
        source : string
            File name or http endpoint containing provenance information.
        format : string
            ID of provenance format. Valid values are: "repronim", "reprozip"

        Returns
        -------
        Provenance sub-class instance
        """
        class_name = format.capitalize() + 'Provenance'
        module = import_module('repronim.provenance.' + format)
        return getattr(module, class_name)(source)

    @staticmethod
    def chain_factory(sources):
        """Factory to load a chain of specifications

        Parameters
        ----------
        sources : list
            List of filenames or http endpoint containing provenance information.

        Raises
        ------
        SpecLoadingError
          if none of the known provenance backends were able to load the sources
        """
        fullspec = None
        for source in sources:
            if fullspec is not None:
                raise RuntimeError(
                    "Loading from multiple specifications is not yet supported")

            # try to guess from the source.  For now just filenames
            _, ext = file_basename(source, return_ext=True)
            candidates = _known_extensions.get(ext, _known_formats)
            for candidate in candidates:
                lgr.debug("Trying to load %s using %s", source, candidate)
                try:
                    # TODO: some will support 'chaining' where previous value
                    # of spec would be passed etc
                    fullspec = Provenance.factory(source, format=candidate)
                except Exception as exc:  # TODO: more specific etc
                    lgr.debug("Failed to load %s using %s: %s" % (
                              source, candidate, exc_str(exc)))
            if fullspec is None:
                raise SpecLoadingError(
                    "Failed to load %s using any known parser" % source)
        return fullspec

    @abc.abstractmethod
    def get_operating_system(self):
        """
        Retrieve the operating system information.

        Returns
        -------
        Dictionary containing name and version of the OS.
            os['name']
            os['version']
        """
        return

    @abc.abstractmethod
    def get_distributions(self):
        """
        Retrieve the information for all the distributions recorded in the
        provenance file.

        Returns
        -------
        list
            List of Distribution sub-class objects.
        """
        return
