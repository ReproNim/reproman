High-level Package Handling (and ReproZip Architecture Discussion)
******************************************************************

What ReproMan aims (not) to be
==============================

We want to leverage existing solutions (such as existing containers, cloud
providers etc), which we will call 'backends', and provide a very high level,
unified API, to interface them with purpose of running computations or
interactive sessions.

We want to concentrate on (re)creation of such computation environments from a
specification which is agnostic of a backend and concentrates on describing
what constitutes the content of that environment relevant for the execution of
computation.  Backend-specific details of construction, execution and
interfacing with the backend should be "templated" (or otherwise parametrized
in sufficient detail) so an advanced user could still provide their tune ups).
We will not aim at the specification to be OS agnostic, i.e. the package
configuration will have terms that are specific to an architecture or
distribution.

Construction of such environments would heavily depend on specification of
"packages" which contain sufficient information to reconstruct and execute in
the environment. Such specifications could be constructed manually, by ReproMan
from loose human description, or via automated provenance collection of "shell"
command.  They also should provide sufficient expressive power to be able to
tune them quickly for most common cases (e.g. upgrade from release X to
release Y)

Packages, Package Managers, and Distributions
=============================================

We would like to be able to identify, record, and install various **packages** of
software and data. A package is a collection of files, potentially platform
specific (in the case of binary packages) or requiring reconstruction (such as
compiling applications from source). In addition, installing a package may have
dependencies (additional packages required by the initial package to correctly
operate). 

Packages are installed, removed, and queried through the use of "package
managers." There are different package managers for different components of an
environment and have slightly different capabilities.  For example, "yum" and
"apt-get" are used to install binary and source files on a Linux operating
system.  "pip" provides download and compilation capability for the Python
interpreted language, while "conda" is another Python package manager that can
supports "virtual environments" (essentially subdirectories) that provide
separate parallel Python environments.  Different packages provide varying amount
of meta-information to identify package a particular file belongs to, or to
gather meta-information identifying that package source so it could be reinstalled
later on (e.g. "pip" from a git repository would not store a URL for that
repository anywhere to be recovered).

A "distribution" is a set of packages (typically organized with their dependencies).
Some distributions (such as Linux distros) are self-sufficient, in a sense
that they could be deployed on a bare hardware or as an independent
virtualized environment which would require nothing else. Many distributions though
allow to mix a number of **origins**, where any package was or could be obtained from.  E.g.
it is multiple apt sources for Debian-based distributions and "channels" in conda.

Some distributions (such as the ones based on PIP, conda), do require some base
environment on top of which they would work.  But also might require some
minimal set of tools being provided by the base environment.  E.g.
`conda` -based distribution would probably need nothing but basic shell (core
OS dependent), and PIP-based would require Python to be installed. Therefore,
there will be a dependency **between** package managers: Operating system
packages (yum & apt-get) will need to be installed first, enabling other
package managers (pip, conda, npm) to then run and build upon the base
packages.

The fundamental challenge of ReproMan's "trace" ability is to identify and
record the package managers, distributions, and packages from the files used in
an experiment. Then to "create" an environment, ReproMan needs to reinstall the
packages from the specification (ideally matching as many properties, such as
version, architecture, size, and hash as possible).

Package Management and Environment Configuration
------------------------------------------------

Here we discuss package managers and key distributions that ReproMan should
cover (and list other potential package managers to consider)

OS Package Managers
~~~~~~~~~~~~~~~~~~~

- apt-get (dpkg) - Expected on Debian and Ubuntu Gnu/Linux distributions
- yum (rpm) - Expected on CentOS/RHEL and other Red Hat Gnu/Linux distributions
- snap - Linux packages (with sandboxed execution) - http://snapcraft.io/

  - Snaps may prove difficult for tracing because commands to download
    and build executibles can be embedded into snap packages

In addition, we should be aware of specific package repositories that will not
stand on their own but depend upon specific OS distributions or configurations:

- NeuroDebian - a key source for NeuroImaging Debian/Ubuntu packages
- other PPAs/APT repositories, e.g. for cran

Finally, OS package managers (and related repositories and distributions) are
typically used to install the language-specific package managers described in
the next section. Therefore, ReproMan "create" will need to install OS packages
first, followed by language-specific packages. We may need to allow the
ReproMan environment specification to allow the user to order the package
installation across multiple package managers to ensure resolution of
dependencies.


Language-Related Package Managers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python

- pip 

  - PyPi Package Index: https://pypi.python.org/pypi

- conda

  - Anaconda Science Platform https://www.continuum.io/downloads
  - Conda-Forge https://conda-forge.github.io/

Others

- npm - node.js
- cpan - Perl
- CRAN - R
- brew, linuxbrew, gems - Ruby

Data Package Managers
~~~~~~~~~~~~~~~~~~~~~

- DataLad

Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

Pretty much in every "computational environment", environment variables are of
paramount importance since they instrument invocation and possibly pointers to
where components would be located when executed. "Overlay" (Non-OS) packages
rely on adjusting (at least) `PATH` env variable so that components they
install, possibly overlaying OS-wide installation components, take precedence.

- virtualenv 

  - Impacts the configuration of python environment (where execution is
    happening, custom python, ENV changes)

- modules

  - http://modules.sourceforge.net
  - Commonly used on HPC, which is the way to "extend" a POSIX distribution.
  - We might want to be aware of it (i.e., being able to detect etc), since it
    could provide at least versioning information which is conventionally
    specified for every installed "module". It might come handy during `trace`
    operation.

Provisioners
~~~~~~~~~~~~

Provisioners allow you to automatically install software, alter configurations,
and maintain files across multiple machines from a central server (or
configuration specification). ReproMan may need to both recognize its use to
create an environment and may have an opportunity to use any of the following
provisioners to recreate an environment:

- ansible
- chef
- puppet
- salt
- fabric


Alternate Installation Approaches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While these are technically not package managers, we may wish to support other
avenues for configuring software to be installed. These approaches may be
impossible to detect automatically:

- VCS in general (git, git-annex) repositories -- we can identify
  if particular files belong to which repo, where it is available from,
  what was the revision etc.  We will not collect/record the entirety of the
  configuration (i.e. all the settings from .git/config), but only the information
  sufficient to reproduce the environment, not necessarily any other possible
  interaction with a given VCS
- Generic URL download
- File and directory copy, move, and rename
- Execution of specific commands - may be highly dependent upon the environment

NOTE: Packages that would generally be considered "Core OS" packages, could be
installed using these alternate approaches


Backends  (engine)
------------------

- native
- docker
- singularity  (could be created from docker container)
- virtualbox
- vagrant
- aws
- chroot/schroot(somewhat Debian specific on my tries)
- more cloud providers? google CE, azure, etc... ?

Engines might need nesting, e.g.

    vagrant > docker
    aws > docker
    ssh > singularity

Image
-----

(inspired by docker and singularity?) What represents a state of computation
environment in a form which could be shared (natively or through some export
mechanism), and/or could be used as a basis for instantiation of multiple
instances or derived environments.

- native -- none?  or in some cases could be a tarball with all relevant pieces (think cde, reprozip)
- docker, singularity -- image
- virtualbox -- virtual appliance
- vagrant -- box (virtualbox appliance with some bells iirc)
- aws -- AMI
- chroot/schroot -- also natively doesn't have an 'image' stage unless we
   easily enforce it -- tarball (or possibly eventually fs/btrfs snapshots etc,
   would be neat) whatever chroot is bootstrapped!


Instance
--------

- native -- none, i.e. there is a singleton instance of the current env
- docker, singularity - container
- virtualbox -- VM instance
- vagrant -- ???
- aws -- instance
- schroot -- session (chroot itself doesn't track anything AFAIK)


Perspective "agents/classes"
============================

Distribution
------------

- bootstrap(spec, backend, instance=None) -> instance/image

    initialize (stage 1)
       which might include batch installation of a number (or all)
       of necessary packages; usually offloaded to some utility/backend.
       (e.g. debootstrap into a dir, docker build from basic Dockerfile, initiate
       aws ami from some image, etc).
       Should return an "instance" we could work with in "customization" stage
    customize (stage 2)
       more interactive (or provisioned) which would tune
       installation by interacting with the environment; so we should provide adapters on how such interaction
       would happen (e.g., we could establish common mechanism via ssh, so every env in stage1
       would then get openssh deployed; but that would not work e.g. for schroot as easily)

  - at the end it should generate backend-appropriate "instance" which could be reused
    for derived containers?
  - overlay distributions would need an existing 'instance' to operate on

static methods (?)
- get_package_url(package, version) -> urls

   - find a URL providing the package of a given version. So, when necessary
     we could download/install those packages

- get_distribution_spec_from_package_list({package: version_spec}) -> spec

   - given a set of desired packages (with version specs), figure out
     distribution specification which would satisfy the specification.
     E.g. to determine which snapshot (which codename, date, components) in
     snapshots.d.o would carry specified packages

# if instance would come out something completely agnostic of the distribution
# since instance could actually "contain" multiple distributions.
# Possibly tricky part is e.g. all APT "Distributions" would share invocation
# -- apt, although could (via temporarily augmenting pin priorities) tune it
# to consider only its part of the distribution for installation... not sure
# if needed
- install(instance, package(s))
- uinstall(instance, package(s))
- upgrade(instance)

Probably not here but in instance...? and not now

- activate() - for those which require changing of ENV.  If we are to allow
   specification of multiple commands where some aren't using the specific
   "distribution" we might want to spec which envs to be used and turn them
   on/off for specific commands
- deactivate()


Image
~~~~~
to be created by bootstrap or "exported" from instance (e.g. "docker commit"
to create an image)

- shrink(spec=None) -> image

  - given a specification (or just some generic cleaning operations) we might
    want to produce a derived image which would be

??? not clear how image/instance would play out when deploying to e.g. HPC.
E.g. having a docker/singularity image, and then running some task which would
require instantiating that image for every job... condor has some builtin
support already IIRC for deploying virtual machine images to run the tasks etc...
familiarize more

Instance (bootstrapped, backend specific)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(many commands inspired by docker?)

- run(command) -> instantiate (possibly new container) environment and run a command
- exec(command) -> run a command in running env
- start(id)
- stop(id)


**or** it would be the resource (AWS, docker, remote HPC) which would be capable of
deploying Instances


Backend
~~~~~~~

???

- should provide mapping from core Distributions specs to native base images
  (e.g. how to get base docker image for specific release of debian/ubuntu, ...;
  which AMIs to use as base, etc)
- we should provide default Core Distributions for case if we have a spec
  only with "overlay" distros (e.g. conda-based)

- bootstrap??

Resource
~~~~~~~~
- instantiate (image, ...) -> instance(s)

  - obtain instance and make it available for execution on the resource
  - some are deployed since were bootstrapped on the resource, but we want to be able to
    deploy new docker image,
  - deployment might result in multiple instances being deployed (master + slaves
    for AWS orchestrated execution or is that at run stage... learn more)


(Possibly naive) questions/TODOs
--------------------------------

- AMI -- could be generated by taking a "snapshot" of existing/running or shutdown instance?

  if not -- we might want to provide a mode where initial "investigation" is
  done locally on a running e.g. docker instance, then script generated for
  customization stage and only then full bootstrap (using one of the available
  tools for AMI provisioning) is used

- docker -- could we export/import an image to get to the same state (possibly losing overlays etc)
- singularity -- the same

Next ones are more in realm of "exec" or "run" aspect which this discussion is
not concentrating on ATM:

- anyone played with StarCluster/ElastiCluster?

- we should familiarize ourselves with built-in features of common PBS systems
  (condor, torque) to schedule jobs which run within containers...

Possibly useful modules/tools
------------------------------

distro-info
    python module for Debian/Ubuntu information about releases. uses data from
    `distro-info-data`
