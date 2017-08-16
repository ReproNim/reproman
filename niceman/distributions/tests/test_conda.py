# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
import collections
import os

import yaml
import attr

try:
    import apt
except ImportError:
    apt = None

import json

from niceman.distributions.conda import CondaTracer


def test_conda_manager_identify_distributions():
    # For now I'm using a local conda install to get a handle on what info
    # is available
    # TODO: Mock or install a real conda environment for testing
    files = ["/home/butch/simple_workflow/miniconda/envs/bh_demo/bin/nipype2boutiques",
             "/home/butch/simple_workflow/miniconda/envs/bh_demo/bin/xz",
             "/home/butch/simple_workflow/miniconda/lib/python3.6/site-packages/pip/utils/ui.py",
             "/sbin/iptables"]
    tracer = CondaTracer()
    dists = list(tracer.identify_distributions(files))

    for (distributions, unknown_files) in dists:
        print(json.dumps(attr.asdict(
                distributions, dict_factory=collections.OrderedDict), indent=4))
        print(json.dumps(unknown_files, indent=4))
