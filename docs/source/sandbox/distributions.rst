High-level brain dumps
**********************

This is just a thinking aloud notes to motivate and structure design decisions.

What ReproNim aims (not) to be
==============================

We want to leverage existing solutions (such as existing containers, cloud
providers etc), which we will call 'backends', and provide a very high level,
unified API, to interface them with purpose of running computations or
interactive sessions.

We want to concentrate on (re)creation of such computation environments from
a specification which is agnostic of a backend and concentrates on describing
what constitutes the content of that environment relevant for the execution
of computation.  Backend-specific details of construction, execution and
interfacing with the backend should be "templated" (or otherwise
parametrized in sufficient detail) so an advanced user could still provide
his/her tune ups).  We will not aim at specification to be OS agnostic, i.e.
terms will be Distribution(s) specific.

Construction of such environments would heavily depend on specification of
"Distribution"s which contain sufficient information to reconstruct and
execute in the environment. Such specifications could be constructed
manually, by ReproNim from loose human description, or via automated
provenance collection of "shell" command.  They also should provide
sufficient expressive power to be able to tune them quickly for most common
cases (e.g. upgrade from release X to release Y)

Distributions
=============

We would like to be able to cover various "distributions" of software (and
data). Distribution as such is just a collection of units, usually called
packages, which allows to manage (install, uninstall, upgrade, ...) via a
unified interface.

Some distributions (such as Linux distros) are self-sufficient, in a sense
that they could be deployed on a bare hardware or as an independent
virtualized environment which would require nothing else.

Some distributions (such as the ones based on PIP, Conda), do require some
base environment on top of which they would work.  But also might require
some minimal set of tools being provided by the base environment.  E.g.
`conda` -based distribution would probably need nothing but basic shell (core
OS dependent), and PIP-based would require Python to be installed.

Known distributions
-------------------
we might want to cover, and underlying distribution "toolkits"

GNU/Linux (Core? OS?)
~~~~~~~~~~~~~~~~~~~~~
- Debian - dpkg, apt
- Ubuntu - dpkg, apt
- CentOS - rpm, yam???

and additional "overlays" in terms of APT repositories

- NeuroDebian
- other PPAs/APT repositories, e.g. for cran

which wouldn't be sufficient on their own.
They "define" the ENV and do not "tune it" to "activate"
They also provide "delivery mechanisms"


Overlay distributions
~~~~~~~~~~~~~~~~~~~~~

Python

- pypi - pip (as the "delivery mechanism", might be used within conda)
- virtualenv - virtualenv (as the environment where execution is happening, custom python, ENV changes)
- Anaconda - conda (see https://www.continuum.io/downloads), ENV changes
- Conda-Forge - conda (see https://conda-forge.github.io/), ENV changes

Others

- ... - npm (for node.js apps)

Data and generic

- DataLad
- VCS in general (git, git-annex) repositories -- we can identify
  if particular files belong to which repo, where it is available from,
  what was the revision etc.

Note that "Core" OS could be deployed in "overlay" mode as well

Backends
--------

- native
- docker
- singularity  (could be created from docker container)
- virtualbox
- vagrant
- aws
- chroot/schroot(somewhat Debian specific on my tries)
- more cloud providers? google CE, azure, etc... ?


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


Overlays: Role of Environment
=============================

Pretty much in every "computational environment", environment variables are
of paramount importance since they instrument invocation and possibly
pointers to where components would be located when executed.  "Overlay
distributions" rely on adjusting (at least) `PATH`
env variable so that components they install, possibly overlaying OS-wide
installation components, take precedence.

There is also `environment modules <http://modules.sourceforge.net>`_ commonly
used on HPC, which is the way to "extend" a POSIX distribution.
Unfortunately, it is not a "distribution" on its own, since it doesn't
provide any means for installation. It just manages (enables/disables)
pre-configured modules.  But I think we might want to be aware of it (i.e.,
being able to detect etc), since it could provide at least versioning
information which is conventionally specified for every installed "module".
It might come handy during `trace` operation.


Overlays: within distro
=======================

Many distributions are "overlayed" within, affecting not the environment variables,
but rather the availability of the packages.  E.g., Debian itself provides:

- multiple suites (`stable`, `testing`, `unstable`, etc) which are aliases to
  "codenames" (release names such as `jessie`, `stretch`, `sid`);
- components (`main`, `contrib`, `non-free`)
- additional repositories for security and other updates (which might come with
  its own components)

so, Debian installation generally is internally an overlay on top of `main` component of some
codename or suite.  And regular stock "debian" sid codename docker container is just that
-- `main`.   But `jessie` (stable) would come with "updates" and "security-updates".  It will be
a pair of `Label` and `Suite` in `*Release` files to describe somewhat uniquely (somewhat) each
APT source::

    root@7b7c55c74d38:/var/lib/apt/lists# grep -e  Label -e Suite -e Components *Release
    httpredir.debian.org_debian_dists_jessie-updates_InRelease:Label: Debian
    httpredir.debian.org_debian_dists_jessie-updates_InRelease:Suite: stable-updates
    httpredir.debian.org_debian_dists_jessie-updates_InRelease:Components: main contrib non-free
    httpredir.debian.org_debian_dists_jessie_Release:Label: Debian
    httpredir.debian.org_debian_dists_jessie_Release:Suite: stable
    httpredir.debian.org_debian_dists_jessie_Release:Components: main contrib non-free
    security.debian.org_dists_jessie_updates_InRelease:Label: Debian-Security
    security.debian.org_dists_jessie_updates_InRelease:Suite: stable
    security.debian.org_dists_jessie_updates_InRelease:Components: updates/main updates/contrib updates/non-free

.. note::
   note that although Components present -- they describe which are available, but
   not necessarily configured

Additional priority mechanism usually is employed to decide which (version of) package should
be installed.  Note that if priorities are set, it is not necesarily that the "most recent"
package would get installed


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

- docker -- could we export/import an image to get to the same state (possibly loosing overlays etc)
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