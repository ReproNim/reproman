# Changelog
All notable changes to this project will be documented (for humans) in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2021-01-28

### Added
- "A typical workflow" section in README.md based on AWS EC2 HTCondor cluster
### Changed
- EC2: easier on user handling of keys, use NITRC-CE AMI by default
### Fixed
- EC2: ability to login to a ec2-condor cluster

## [0.3.1] - 2021-01-25

Minor feature and bug fix release
### Added
- use of etelemetry
- initial support for LSF submitted
### Fixed
- testing of venv tracking
- setting of `DATALAD_SSH_IDENTITYFILE` earlier (in `__init__`) for DataLad orchestrator

## [0.3.0] - 2020-10-21
Feature and bug fix release after a long release silence.
### Added
- `run` - support for SLURM submitter
- `full-except-datalad` setuptools installation "extra_requires" scheme
- `AwsCondor` resource type to assist in establishing a simple HPC cluster with
  condor as ubmitted in AWS S3
- `put`, `get` of implemented resources got a recursive mode
### Changed
- `run`- switch to use use GNU parallel instead of the one from moreutils
  for local execution
- fixed up/improved documentation (in particular for `run`)
- use `docker>=3` instead of `docker-py`
### Fixed
- a wide variety of fixes
### Removed
- python 3.5 support

## [0.2.1] - 2019-10-18
Yarik needed to do a quick release to absorb changes to `run`
functionality.

## [0.2.0] - 2019-09-11
Major rename - a NICEMAN grows into a ReproMan.  Too many changes to summarize
### Added
- `reproman run` to execute computation on local or remote resource, with
  possibility to submit computation to PBS and Condor.

## [0.1.0] - 2018-12-18
Largely bugfixes and small enhancements. Major work is ongoing in PRs
to provide new functionality (such as remote execution and environment
comparisons)
### Added
- Tracing RPM-based (RedHat, CentOS) environments
- Tracing Singularity images
### Fixed
- A variety of fixes and enhances in tracing details of git, conda,
  etc resources.
- interactive ssh sessions fixes through use of `fabric` module instead of
  custom code
### Changed
- Refactored handling of resource parameters to avoid code duplication/boiler
  plate

## [0.0.6] - 2018-06-17
Enhancement and fixes primarily targetting better tracing (collecting
information about) of the computational components
### Added
- tracing of
  - docker images
- `diff` command to provide summary of differences between two specs
- conda environments could be regenerated from the environments
### Changed
- relative paths could be provided to the `retrace` command
### Fixed
- tracing of Debian packages and Git repositories should be more robust
  to directories
- handling of older `conda` environments

## [0.0.5] - 2018-01-05
Minor release with a few fixes and performance enhancements
### Added
- Create apt .sources files pointing to APT snapshot repositories
### Performance
- Batch commands invocations in Debian tracer to significantly speed up
  retracing
### Fixed
- Output of the (re)traced spec into a file

## [0.0.3] - 2017-12-19
A minor release to demonstrate `retrace` functionality

---

Just a template for future records:

## [Unreleased] - Date
TODO Summary
### Added
### Changed
### Deprecated
### Fixed
### Removed
### Security

---

## References
[datalad]: http://datalad.org
[reproman]: http://reproman.repronim.org
[repronim]: http://repronim.org
[simple_workflow]: https://github.com/ReproNim/simple_workflow
