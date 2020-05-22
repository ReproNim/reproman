#!/bin/bash

set -eu

export PS4="> "

set -x
setup=${1:-pip}
cd "$(mktemp -d ${TMPDIR:-/tmp}/rm-XXXXXXX)"

trap "echo Finished for setup=$setup under PWD=`pwd`" SIGINT SIGHUP SIGABRT EXIT

py=3
d=venv$py;
(
virtualenv --python=python$py --system-site-packages $d
) 2>&1 | tee venv-setup.log

source "$d/bin/activate"  # should be outside of () to take effect

(
case "$setup" in
 kyle1)
   # Kyle's setup from https://github.com/ReproNim/reproman/issues/511#issuecomment-632776223
  pip install git+http://github.com/datalad/datalad@53765be03838ee8b07d4b44a2a27bbbe259fe160
  # This one seems to be for older datalad
  pip install git+http://github.com/ReproNim/reproman@a9c9842302cad707bbdaf56fa4050fe0136ffe23
  # with unbuffered io:
  #pip install git+http://github.com/ReproNim/reproman@4f05f3aa96c7ab550aa218d5de705ea3cfe5f600
  ;;
 debug1) # the "default
  # Current master of datalad
  pip install git+http://github.com/datalad/datalad@0.13.0rc1-109-g7f24491b2
  # ReproMan PR https://github.com/ReproNim/reproman/pull/506 with support of datalad master
  pip install git+http://github.com/kyleam/niceman@v0.2.1-80-g45baab0
  ;;
 pip)  # should be our target -- install via pip everything and it must be working
   pip install datalad reproman;;
 *)
   echo "Unknown setup $setup" >&2
   exit 1
   ;;
esac

# in either of the cases default datalad-container should be ok
pip install datalad-container

# Actual script to run from the current state of the PR
# https://github.com/ReproNim/reproman/pull/438
wget https://raw.githubusercontent.com/ReproNim/reproman/b70144e993660c271831e4ea8d2f4bb436bb7eeb/docs/usecases/bids-fmriprep-workflow-NP.sh
) 2>&1 | tee install.log

(
    BIDS_APPS=mriqc FS_LICENSE=bogus RM_ORC=datalad-pair bash ./bids-fmriprep-workflow-NP.sh output
) 2>&1 | tee run.log