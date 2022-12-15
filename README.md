# ReproMan

[![Supports python version](https://img.shields.io/pypi/pyversions/datalad)](https://pypi.org/project/datalad/)
[![GitHub release](https://img.shields.io/github/release/ReproNim/reproman.svg)](https://GitHub.com/ReproNim/reproman/releases/)
[![PyPI version fury.io](https://badge.fury.io/py/reproman.svg)](https://pypi.python.org/pypi/reproman/)
[![Tests](https://github.com/ReproNim/reproman/workflows/Tests/badge.svg)](https://github.com/ReproNim/reproman/actions?query=workflow%3ATests)
[![codecov.io](https://codecov.io/github/ReproNim/reproman/coverage.svg?branch=master)](https://codecov.io/github/ReproNim/reproman?branch=master)
[![Documentation](https://readthedocs.org/projects/reproman/badge/?version=latest)](https://reproman.readthedocs.io/en/latest/?badge=latest)


ReproMan aims to simplify creation and management of computing environments
in Neuroimaging.  While concentrating on Neuroimaging use-cases, it is
by no means is limited to this field of science and tools will find
utility in other fields as well.

# Status

ReproMan is under rapid development. While
the code base is still growing the focus is increasingly shifting towards
robust and safe operation with a sensible API. There has been no major public
release yet, as organization and configuration are still subject of
considerable reorganization and standardization. 


See [CONTRIBUTING.md](CONTRIBUTING.md) if you are interested in
internals and/or contributing to the project.

# Installation

TODO(asmacdo) Set up sphinx substitution
ReproMan requires Python 3 (>= |MinPython|).

## Linux'es and OSX (Windows yet TODO) - via pip

By default, installation via pip (`pip install reproman`) installs core functionality of reproman
allowing for managing datasets etc.  Additional installation schemes
are available, so you could provide enhanced installation via
`pip install 'reproman[SCHEME]'` where `SCHEME` could be

- tests
     to also install dependencies used by unit-tests battery of the reproman
- full
     to install all of possible dependencies, e.g. [DataLad](http://datalad.org)

For installation through `pip` you would need some external dependencies
not shipped from it (e.g. `docker`, `singularity`, etc.) for which please refer to
the next section.  

## Debian-based systems

On Debian-based systems we recommend to enable [NeuroDebian](http://neuro.debian.net)
from which we will soon provide recent releases of ReproMan.  We will also provide backports of
all necessary packages from that repository.


## Dependencies

Our `setup.py` and corresponding packaging describes all necessary dependencies.
On Debian-based systems we recommend to enable [NeuroDebian](http://neuro.debian.net)
since we use it to provide backports of recent fixed external modules we
depend upon.  Additionally, if you would
like to develop and run our tests battery see [CONTRIBUTING.md](CONTRIBUTING.md)
regarding additional dependencies.

# A typical workflow for `reproman run`

This example is heavily based on the ["Typical workflow"](https://github.com/ReproNim/containers/#a-typical-workflow)
example created for [///repronim/containers](https://github.com/ReproNim/containers/)
which we refer you to discover more about YODA principles etc.  In this reproman example we will
follow exactly the same goal -- running MRIQC on a sample dataset -- but this time utilizing
ReproMan's ability to run computation remotely. DataLad and `///repronim/containers` will
still be used for data and containers logistics, while reproman will establish a little [HTCondor](https://research.cs.wisc.edu/htcondor/)
cluster in the AWS cloud, run the analysis, and fetch the results.

## Step 1: Create the HTCondor AWS EC2 cluster

If it is the first time you are using ReproMan to interact with AWS cloud services, you should first provide
ReproMan with secret credentials to interact with AWS. For that edit its configuration file
(`~/.config/reproman/reproman.cfg` on Linux, `~/Library/Application Support/reproman/reproman.cfg` on OSX)

    [aws]
    access_key_id = ...
    secret_access_key = ...

**Disclaimer/Warning: Never share or post those secrets publicly.**

filling out the `...`s.  If `reproman` fails to find this information, error message `Unable to locate credentials` will appear.

Run (need to be done once, makes resource available for `reproman login` or `reproman run`):

```shell
reproman create aws-hpc2 -t aws-condor -b size=2 -b instance_type=t2.medium
```
to create a new ReproMan resource: 2 AWS EC2 instances, with HTCondor installed (we use [NITRC-CE](https://www.nitrc.org/projects/nitrc_es/) instances).

**Disclaimer/Warning: It is important to monitor your cloud resources in the cloud provider dashboard(s)
to ensure absent run away instances etc. to help avoid incuring heavy cost for used cloud services.**

## Step 2: Create analysis DataLad dataset and run computation on aws-hpc2

Following script is an exact replica from [///repronim/containers](https://github.com/ReproNim/containers/#a-typical-workflow)
where only the `datalad containers-run` command, which fetches data locally and runs computation locally and serially, is replaced with
`reproman run` which publishes dataset (without data) to the remote resource, fetches the data, runs computation
via HTCondor in parallel across 2 nodes, and then fetches results back:

```shell
#!/bin/sh
(  # so it could be just copy pasted or used as a script
PS4='> '; set -xeu  # to see what we are doing and exit upon error
# Work in some temporary directory
cd $(mktemp -d ${TMPDIR:-/tmp}/repro-XXXXXXX)
# Create a dataset to contain mriqc output
datalad create -d ds000003-qc -c text2git
cd ds000003-qc
# Install our containers collection:
datalad install -d . ///repronim/containers
# (optionally) Freeze container of interest to the specific version desired
# to facilitate reproducibility of some older results
datalad run -m "Downgrade/Freeze mriqc container version" \
    containers/scripts/freeze_versions bids-mriqc=0.16.0
# Install input data:
datalad install -d . -s https://github.com/ReproNim/ds000003-demo sourcedata
# Setup git to ignore workdir to be used by pipelines
echo "workdir/" > .gitignore && datalad save -m "Ignore workdir" .gitignore
# Execute desired preprocessing in parallel across two subjects
# on remote AWS EC2 cluster, creating a provenance record
# in git history containing all condor submission scripts and logs, and
# fetching them locally
reproman run -r aws-hpc2 \
   --sub condor --orc datalad-pair \
   --jp "container=containers/bids-mriqc" --bp subj=02,13 --follow \
   --input 'sourcedata/sub-{p[subj]}' \
   --output . \
   '{inputs}' . participant group -w workdir --participant_label '{p[subj]}'
)
```
[ReproMan: Execute](https://reproman.readthedocs.io/en/latest/execute.html) documentation section
provides more information on the underlying principles behind [`reproman run`](https://reproman.readthedocs.io/en/latest/generated/man/reproman-run.html)
command.

## Step 3: Remove resource

Whenever everything is computed and fetched, and you are satisfied with the results, use `reproman delete aws-hpc2` to terminate
remote cluster in AWS, to not cause unnecessary charges.

# License

MIT/Expat


# Disclaimer

It is in a beta stage -- majority of the functionality is usable but
Documentation and API enhancements is WiP to make it better.  Please do not be
shy of filing an issue or a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md)
for the guidance.

[Git]: https://git-scm.com
[Git-annex]: http://git-annex.branchable.com
