# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of Vagrant instances."""

from repronim.orchestrator.base import Orchestrator

class VagrantOrchestrator(Orchestrator):

    def __init__(self, provenance):
        super(VagrantOrchestrator, self).__init__(provenance)

    def install_packages(self):
        return