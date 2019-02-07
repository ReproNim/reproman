# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import join as opj, dirname

# Configuration file for testing
REPROMAN_CFG_PATH = opj(dirname(__file__), 'files', 'reproman.cfg')
REPROMAN_CFG = open(REPROMAN_CFG_PATH).read()
