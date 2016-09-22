# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of AWS services."""

from repronim.orchestrator.base import Orchestrator

class AwsOrchestrator(Orchestrator):

    def __init__(self, provenance):
        super(AwsOrchestrator, self).__init__(provenance)

    def install_packages(self):
        return