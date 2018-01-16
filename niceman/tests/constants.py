# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import join as opj, dirname

# TODO: move upstairs

# Configuration file for testing
NICEMAN_CFG_NAME = 'niceman.cfg'
NICEMAN_INVENTORY_NAME = 'inventory.yml'
NICEMAN_CFG_SAMPLE_PATH = opj(dirname(__file__), 'files', NICEMAN_CFG_NAME)
# NICEMAN_CFG = open(NICEMAN_CFG_SAMPLE_PATH).read()
