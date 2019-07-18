#!/bin/bash
#emacs: -*- mode: shell-script; c-basic-offset: 4; tab-width: 4; indent-tabs-mode: t -*- 
#ex: set sts=4 ts=4 sw=4 noet:
#
#  This script is intended to demonstrate a sample workflow on a BIDS
#  dataset using mriqc, fmriprep, and custom analysis pipeline, mimicing the
#  steps presented in an fmriprep paper currently under review but using
#  DataLad, ReproNim/containers, and ReproNim.
#
# COPYRIGHT: Yaroslav Halchenko 2019
#
# LICENSE: MIT
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
#

set -eu

# $STUDY is a variable used in a paper this workflow mimics
STUDY="$1"

# Create study dataset
datalad create -c text2git "$STUDY"
cd "$STUDY"

#
# Install containers dataset for guaranteed/unambigous containers versioning
# and datalad containers-run
#
# TODO: specific version, TODO - reference datalad issue
datalad install -d . ///repronim/containers

# possibly downgrade versions to match the ones used in the "paper"
# TODO see  https://github.com/ReproNim/containers/issues/8 for relevant discussion
# and possibly providing some helper to accomplish that more easily
cd containers
echo -n "\
poldracklab-ds003-example	0.0.3
bids-mriqc					0.15.0
bids-fmriprep				1.4.1
"| while read img ver; do
	git config -f .datalad/config --replace-all datalad.containers.$img.image images/${img%%-*}/${img}--${ver}.sing;
done
datalad save -d^ -m "Possibly downgraded containers versions to the ones in the paper" $PWD/.datalad/config
cd ..

#
# Install dataset to be analyzed (no data - analysis might run in the cloud or on HPC)
#
# In original paper name for the dataset was used as is, and placed at the
# top level.  Here, to make this demo easier to apply to other studies,
# and also check on other datasets, we install input dataset under a generic
# "data/bids" path.  "data/" will also collect all other derivatives etc
mkdir data

# For now we will work with minimized version with only 2 subjects
# datalad install -d . -s ///openneuro/ds000003 data/bids
datalad install -d . -s https://github.com/ReproNim/ds000003-demo data/bids


#
# Licenses
#

# we will not prepopulate this one
mkdir licenses/
echo freesurfer.txt > licenses/.gitignore

cat > licenses/README.md <<EOF

Freesurfer
----------

Place your FreeSurfer license into freesurfer.txt file in this directory.
Visit https://surfer.nmr.mgh.harvard.edu/registration.html to obtain one if
you don't have it yet - it is free.

EOF
datalad save -m "DOC: licenses/ directory stub" licenses/


#
# Execution.
#
# That is where access to the powerful resource (HPC) etc would be useful.
# Every of those containerized apps might need custom options to be added.
#
#

# Define common parameters for the reproman run

# ReproMan orchestrator to be used - determines how data/results would be
# transferred and execution protocoled
# Use  reproman run --list orchestrators  to get an updated list
RM_ORC=datalad-pair-run  # ,plain,datalad-pair,datalad-local-run

# Which batch processing system supported by ReproMan will be used
# Use  reproman run --list submitters  to get an updated list
# RM_SUB=condor,pbs,local

# Which resource to use
# It would require (if was not done before) to configure
# a resource where execution will happen.  For now will just use smaug below.
# TODO: provide pointers to doc ( ;-) )
# RM_RESOURCE=

#RM_RESOURCE=discovery
#RM_SUB=PBS
#
# Necessary modules to be loaded in that session:
#  - singularity/2.4.2
# Necessary installations/upgrades to be done (TODO: contact John)
#  - datalad (0.11.6, TODO: release first)
#  - datalad-container

RM_RESOURCE=smaug
RM_SUB=condor

# TODO: at reproman level allow to specify ORC and SUB for a resource, so there would
#   be no need to specify for each invocation.  Could be a new (meta) resource such as
#   "smaug-condor" which would link smaug physical resource with those parameters
# TODO: point to the issue in ReproMan

# 1. bids-mriqc -- QA

# Q/TODO: Is there a way to execute/reference the container?
#   for now doing manually
reproman run --follow -r "${RM_RESOURCE}" --sub "${RM_SUB}" --orc "${RM_ORC}" \
  --bp 'thing=thing-*' \
  --input '{p[thing]}' \
  sh -c 'cat {p[thing]} {p[thing]} >doubled-{p[thing]}'

# 2. bids-fmriprep -- preprocessing

# 3. poldracklab-ds003-example -- analysis

# X. Later? visualization etc - used nilearn
