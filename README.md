# NICEMAN

NICEMAN aims to simplify creation and management of computing environments
in Neuroimaging.  While concentrating on Neuroimaging use-cases, it is
by no means is limited to this field of science and tools will find
utility in other fields as well.

# Status

NICEMAN is under initial rapid development to establish core functionality.  While
the code base is still growing the focus is increasingly shifting towards
robust and safe operation with a sensible API. There has been no major public
release yet, as organization and configuration are still subject of
considerable reorganization and standardization. 


See [CONTRIBUTING.md](CONTRIBUTING.md) if you are interested in
internals and/or contributing to the project.

## Code status:

* [![Travis tests status](https://secure.travis-ci.org/ReproNim/niceman.png?branch=master)](https://travis-ci.org/ReproNim/niceman) travis-ci.org (master branch)

* [![codecov.io](https://codecov.io/github/ReproNim/niceman/coverage.svg?branch=master)](https://codecov.io/github/ReproNim/niceman?branch=master)

* [![Documentation](https://readthedocs.org/projects/NICEMAN/badge/?version=latest)](http://niceman.rtfd.org)

# Installation

## Debian-based systems

On Debian-based systems we recommend to enable [NeuroDebian](http://neuro.debian.net)
from which we will soon provide recent releases of NICEMAN (as soon as
there is something to release).  We will also provide backports of
all necessary packages from that repository.

## Other Linux'es, OSX (Windows yet TODO) via pip

By default, installation via pip installs core functionality of niceman
allowing for managing datasets etc.  Additional installation schemes
are available, so you could provide enhanced installation via
`pip install niceman[SCHEME]` where `SCHEME` could be

- tests
     to also install dependencies used by unit-tests battery of the niceman
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

Later we will provide bundled installations of NICEMAN across popular
platforms.


# License

MIT/Expat


# Disclaimer

It is in a alpha stage -- **nothing** is set in stone yet and nothing is
usable ATM -- subscribe and wait for the first release.

[Git]: https://git-scm.com
[Git-annex]: http://git-annex.branchable.com
