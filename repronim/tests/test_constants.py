# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import join as opj, dirname

# Sample output from Reprozip.
REPROZIP_SPEC1_YML_FILENAME = opj(dirname(__file__), 'files', 'reprozip_spec1.yml')
REPROZIP_SPEC1 = open(REPROZIP_SPEC1_YML_FILENAME).read()

# examples/demo_spec1.yml
DEMO_SPEC1_YML_FILENAME = opj(dirname(__file__), 'files', 'demo_spec1.yml')
DEMO_SPEC1 = open(DEMO_SPEC1_YML_FILENAME).read()
