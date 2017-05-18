# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to identify package sources for files"""

from __future__ import unicode_literals

import time
from logging import getLogger

from niceman.distributions.debian import DebTracer


lgr = getLogger('niceman.api.retrace')



# TODO: environment should be with a state.  Idea is that if we want
#  to trace while inheriting all custom PATHs which that run might have
#  had
def identify_packages(files, environment=None):
    """Identify packages files belong to

    Parameters
    ----------
    files : iterable
      Files to consider

    Returns
    -------
    packages : list of Package
    origins : list of Origin
    unknown_files : list of str
      Files which were not determined to belong to some package
    """
    # TODO: move this function into the base.py having decided on naming etc
    from .vcs import VCSTracer
    # TODO create list of appropriate for the `environment` OS tracers
    #      in case of no environment -- get current one
    tracers = [DebTracer(), VCSTracer()]
    origins = []
    packages = []

    files_to_consider = files

    for tracer in tracers:
        begin = time.time()
        # TODO: we should allow for multiple passes, where each one could
        #  possibly identify a new "distribution" (e.g. scripts ran from
        #  different virtualenvs... some bizzare multiple condas etc)
        # Each one should initialize "Distribution" and attach to it pkgs
        (packages_, unknown_files) = \
            tracer.identify_packages_from_files(files_to_consider)
        # TODO: tracer.normalize
        #   similar to DBs should take care about identifying/groupping etc
        #   of origins etc
        packages_origins = tracer.identify_package_origins(packages_)

        if packages_origins:
            origins += packages_origins
        lgr.debug("Assigning files to packages by %s took %f seconds",
                  tracer, time.time() - begin)
        packages += packages_
        files_to_consider = unknown_files

    return packages, origins, files_to_consider
