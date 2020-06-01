#!/bin/bash
#emacs: -*- mode: shell-script; c-basic-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 et:
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
#  Description
#
#  Environment variables
#   - RUNNER - datalad or reproman (default: reproman)
#   - Options to  reproman run  invocation
#     - RM_ORC - orchestrator to use (default: datalad-pair-run)
#     - RM_RESOURCE - resource to use (default: local)
#     - RM_SUBMITTED - submitter to use (default: local)
#   - BIDS_APPS - if set -- ,-separated list of apps to consider (out of
#     mriqc and fmriprep ATM)
#   - FS_LICENSE - filename or content of the license for freesurfer
#   - CONTAINERS_REPO - an alternative (could be local) location for containers
#                       repository.
#     Make sure that you have got the images for specific versions we freeze to below:
#       datalad get images/bids/bids-mriqc--0.15.0.sing images/bids/bids-fmriprep--1.4.1.sing
#
#   - INPUT_DATASET_REPO - an alternative (could be local) location for input
#                       BIDS dataset
#
#  Note that if FS_LICENSE does not point to a file and is not empty, it would
#  assume to contain the license content.  If you are not interested in running
#  only MRIQC, just set it to some bogus value.
#  So to run only mriqc if you don't have freesurfer license, do
#  BIDS_APPS=mriqc FS_LICENSE=bogus ...
#
#  Sample invocations
#   - Pointing to the existing local clones of input repositories for faster
#     "get"
#     RUNNER=datalad \
#       FS_LICENSE=~/.freesurfer-license \
#       CONTAINERS_REPO=~/proj/repronim/containers \
#       INPUT_DATASET_REPO=$PWD/bids-fmriprep-workflow-NP/ds000003-demo \
#       ./bids-fmriprep-workflow-NP.sh bids-fmriprep-workflow-NP/out2
#

set -eu
export PS4='ex:$? > '
set -x

# $STUDY is a variable used in a paper this workflow mimics
STUDY="$1"

#  Which runner - reproman or datalad
: "${RUNNER:=reproman}"

# Define common parameters for the reproman run

# ReproMan orchestrator to be used - determines how data/results would be
# transferred and execution protocoled
# Use  reproman run --list orchestrators  to get an updated list
: "${RM_ORC:=datalad-pair-run}"  # ,plain,datalad-pair,datalad-local-run

# Which batch processing system supported by ReproMan will be used
# Use  reproman run --list submitters  to get an updated list
# RM_SUB=condor,pbs,local

# Which resource to use
# It would require (if was not done before) to configure
# a resource where execution will happen.  For now will just use smaug below.
# TODO: provide pointers to doc ( ;-) )

# On discovery resource use PBS, and
# Necessary modules to be loaded in that session:
#  - singularity/2.4.2
# Necessary installations/upgrades to be done (TODO: contact John)
#  - datalad (0.11.6, TODO: release first)
#  - datalad-container

: "${RM_RESOURCE:=local}"
: "${RM_SUB:=local}"

# TODO: at reproman level allow to specify ORC and SUB for a resource, so there would
#   be no need to specify for each invocation.  Could be a new (meta) resource such as
#   "smaug-condor" which would link smaug physical resource with those parameters
# TODO: point to the issue in ReproMan


unknown_runner () {
    echo "ERROR: Unknown runner $RUNNER.  Known reproman and datalad" >&2
    exit 1
}

# Common invocation of ReproMan
# TODO: just make it configurable per project/env?
reproman_run () {
    reproman run --follow -r "${RM_RESOURCE}" --sub "${RM_SUB}" --orc "${RM_ORC}" "$@"
}


# TODO: see where such functionality could be provided within reproman, so could
# be easily reused
get_participant_ids () {
    # Would go through provided paths and current directory to find participants.tsv
    # and return participant ids, comma-separated
    for p in "$@" .; do
        f="$p/participants.tsv"
        if [ -e "$f" ]; then
            awk -F'\t' '/^sub-/{print $1}' "$f" \
                | sed 's/sub-//' \
                | tr '\n' ',' \
                | sed -e 's/,$//g'
            break
        fi
    done
}

function run_bids_app() {
    app="$1"; shift
    do_group="$1"; shift
    app_args=( "$@" -w work )

    if [ -n "${BIDS_APPS:=}" ] && ! echo "$BIDS_APPS" | grep -q "\<$app\>" ; then
      echo "I: skipping $app since BIDS_APPS=$BIDS_APPS"
      return
    fi
    outds=data/$app
    container=containers/bids-$app
    app_runner_args=( --input containers/licenses --output "$outds" )

    mkdir -p work
    grep -e '^work$' .gitignore \
    || { echo "work" >> .gitignore; datalad save -m "Ignore work directory"; }

    # set -x
    # Create target output dataset
    # TODO: per app specific configuration?  some might have too heavy xml etc
    # files
    [ -e "$outds" ] || datalad create -d . -c text2git "$outds"

    case "$RUNNER" in
        reproman)
            # Serial run
            # reproman_run --jp container=containers/bids-mriqc "${RUNNER_ARGS[@]}" "${MRIQC_ARGS[@]}"
            # Parallel requires two runs -- parallel across participants:
            reproman_run --jp "container=$container" "${app_runner_args[@]}" \
                 --input "data/bids/sub-{p[pl]}" \
                 --bp "pl=$(get_participant_ids data/bids)" \
                 data/bids '{outputs}' participant --participant_label '{p[pl]}' "${app_args[@]}"
            case "$do_group" in
                1|yes)
                    # serial for the group
                    reproman_run --jp "container=$container" "${app_runner_args[@]}" \
                        --input "data/bids" \
                        '{inputs}' '{outputs}' group "${app_args[@]}"
                    ;;
                0|no)
                    ;;
                *)
                    echo "Unknown value APP_GROUP=$do_group" >&2
                    exit 1
                    ;;
            esac
        ;;
        datalad)
            # Note: this is not in effect!  TODO
            case "$do_group" in
                1|yes) app_args=( group "${app_args[@]}" ) ;;
                0|no) ;;
                *) exit 1 ;;
            esac
            datalad containers-run -n "$container" "${app_runner_args[@]}" \
                '{inputs}' '{outputs}' participant "${app_args[@]}"
            ;;
        *) unknown_runner;;
    esac
    # set +x
}

#
# Check asap for licenses since fmriprep needs one for FreeSurfer
#

if [ -z "${FS_LICENSE:-}" ]; then
    if [ -e "${FREESURFER_HOME:-/XXXX}/.license" ]; then
        FS_LICENSE="${FREESURFER_HOME}/.license"
    else
        cat >&2 <<EOF
Error: No FreeSurfer license found!
    Either define FREESURFER_HOME environment variable pointing to a directory
    with .license file for FreeSurfer or define FS_LICENSE environment variable
    which would either point to the license file or contain the license
    (with "\\n" for new lines) to be used for FreeSurfer
EOF
        exit 1
    fi
fi


# Create study dataset
datalad create -c text2git "$STUDY"
cd "$STUDY"

#
# Install containers dataset for guaranteed/unambigous containers versioning
# and datalad containers-run
#
# TODO: specific version, TODO - reference datalad issue

# Local copy to avoid heavy network traffic while testing locally could be
# referenced in CONTAINERS_REPO env var
datalad install -d . -s "${CONTAINERS_REPO:-///repronim/containers}"

# TODO: shift that into some helper script in the containers
CONTAINERS_FS_LICENSE=containers/licenses/freesurfer
if [ -e "$FS_LICENSE" ]; then
    cp "$FS_LICENSE" "$CONTAINERS_FS_LICENSE"
else
    echo -n "$FS_LICENSE" >| "$CONTAINERS_FS_LICENSE"
fi
datalad save -d . -m "Added licenses/freesurfer (needed for fmriprep)" containers/licenses/
( cd containers; git annex metadata licenses/freesurfer -s distribution-restrictions=sensitive; )


# possibly downgrade versions to match the ones used in the "paper"
containers/scripts/freeze_versions --save-dataset=^ \
    poldracklab-ds003-example=0.0.3 \
    bids-mriqc=0.15.0 \
    bids-fmriprep=1.4.1

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
datalad install -d . -s "${INPUT_DATASET_REPO:-https://github.com/ReproNim/ds000003-demo}" data/bids

#
# Execution.
#
# That is where access to the powerful resource (HPC) etc would be useful.
# Every of those containerized apps might need custom options to be added.
#
#

# datalad save -d . -m "Due to https://github.com/datalad/datalad/issues/3591" data/mriqc


run_bids_app mriqc yes
# note: not using $CONTAINERS_FS_LICENSE just to make things a bit more explicit
run_bids_app fmriprep no --fs-license-file=containers/licenses/freesurfer

# 3. poldracklab-ds003-example -- analysis

# X. Later? visualization etc - used nilearn


exit 0  # done for now


reproman run --follow -r "${RM_RESOURCE}" --sub "${RM_SUB}" --orc "${RM_ORC}" \
  --bp 'thing=thing-*' \
  --input '{p[thing]}' \
  sh -c 'cat {p[thing]} {p[thing]} >doubled-{p[thing]}'


