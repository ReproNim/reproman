# ReproMan

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

## Code status:

* [![Travis tests status](https://secure.travis-ci.org/ReproNim/reproman.png?branch=master)](https://travis-ci.org/ReproNim/reproman) travis-ci.org (master branch)

* [![codecov.io](https://codecov.io/github/ReproNim/reproman/coverage.svg?branch=master)](https://codecov.io/github/ReproNim/reproman?branch=master)

* [![Documentation](https://readthedocs.org/projects/ReproMan/badge/?version=latest)](http://reproman.rtfd.org)

# Installation

ReproMan requires Python 3 (>= 3.6).

## Debian-based systems

On Debian-based systems we recommend to enable [NeuroDebian](http://neuro.debian.net)
from which we will soon provide recent releases of ReproMan (as soon as
there is something to release).  We will also provide backports of
all necessary packages from that repository.

## Other Linux'es, OSX (Windows yet TODO) via pip

By default, installation via pip installs core functionality of reproman
allowing for managing datasets etc.  Additional installation schemes
are available, so you could provide enhanced installation via
`pip install reproman[SCHEME]` where `SCHEME` could be

- tests
     to also install dependencies used by unit-tests battery of the reproman
- full
     to install all of possible dependencies.

For installation through `pip` you would need some external dependencies
not shipped from it (e.g. `docker`, `singularity`, etc.) for which please refer to
the next section.  

## Dependencies

Our `setup.py` and corresponding packaging describes all necessary dependencies.
On Debian-based systems we recommend to enable [NeuroDebian](http://neuro.debian.net)
since we use it to provide backports of recent fixed external modules we
depend upon.  Additionally, if you would
like to develop and run our tests battery see [CONTRIBUTING.md](CONTRIBUTING.md)
regarding additional dependencies.

Later we will provide bundled installations of ReproMan across popular
platforms.


# License

MIT/Expat


# Disclaimer

It is in a beta stage -- majority of the functionality is usable but
Documentation and API enhancements is WiP to make it better.  Please do not be
shy of filing an issue or a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md)
for the guidance.

[Git]: https://git-scm.com
[Git-annex]: http://git-annex.branchable.com
