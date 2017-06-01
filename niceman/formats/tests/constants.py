# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import join as opj, dirname

# Sample output from Reprozip.
REPROZIP_SPEC1_YML_FILENAME = opj(dirname(__file__), 'files', 'reprozip_spec1.yml')
REPROZIP_SPEC2_YML_FILENAME = opj(dirname(__file__), 'files', 'reprozip_xeyes.yml')

# examples/demo_spec1.yml
NICEMAN_SPEC1_YML_FILENAME = opj(dirname(__file__), 'files', 'nicemanspec1_v0.0.1.yml')
NICEMAN_SPEC1_YML = open(NICEMAN_SPEC1_YML_FILENAME).read()

