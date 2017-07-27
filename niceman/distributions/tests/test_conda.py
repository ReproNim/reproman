# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os
try:
    import apt
except ImportError:
    apt = None

from pprint import pprint

from niceman.distributions.conda import CondaTracer


def test_conda_manager_identify_distributions():
    # For now I'm using a local conda install to get a handle on what info
    # is available
    files = ["/home/butch/simple_workflow/miniconda/envs/bh_demo/bin/nipype2boutiques",
             "/home/butch/simple_workflow/miniconda/envs/bh_demo/bin/xz"]
    tracer = CondaTracer()
    dists = list(tracer.identify_distributions(files))
    for (distributions, unknown_files) in dists:
        pprint(distributions)
        pprint(unknown_files)
#    distribution, unknown_files = distributions[0]
#    pprint(distribution)
