# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Orchestrator sub-class to provide management of the localhost environment."""

from repronim.orchestrator.base import Orchestrator
import subprocess

from repronim.cmd import Runner

class LocalhostOrchestrator(Orchestrator):

    def __init__(self, provenance):
        super(LocalhostOrchestrator, self).__init__(provenance)

    def install_packages(self):

        for package in self.provenance.get_packages():
            self.lgr.debug("Installing package: %s" % package['name'])
            command = [
                'apt-get',
                'install',
                '-y',
                package['name']
            ]
            run = Runner()
            output = run(command, shell=True)
            self.lgr.debug(output)  # Send the call response to the screen.
