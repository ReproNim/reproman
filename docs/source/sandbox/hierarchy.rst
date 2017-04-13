Current hierarchy
-----------------

Matt side
*********

distribution.base.Distribution   base class
===============================

 - __init__ (provenance)
 - factory [static]  (distribution_name, provenance)
    provenance given to __init__
 - initiate (environment)
 - install_packages (environment)

sub-classes
 - Debian
 - NeuroDebian
 - pypi
 - conda

TOL (thoughts out loud):
- just gets a "provenance" so not clear from API what it needs and operates on.
  It relies on "provenance" which is passed into the constructor and which
  it later 'uses' for any of the steps.
  That makes it somewhat inflexible since probably "orchestrating" of the
  Distribution's should be done outside of their classes, and they should just
  be provided necessary pieces of the "provenance" depending on their types.
  So e.g. `install_packages` should get a list of versioned packages and the `environment`
  to be used to install them

  - __init__()  -- leave agnostic of the "provenance"

  - initiate(
     origins: list of the origins to initiate based on,
     environment: the environment to operate in
    )

    might want to do
    - necessary checks if environment is compatible with this distribution and
      possibly is already satisfied (could be useful to be able to use functionality
      from trace!)
    - instruct already pre-setup environment to install necessary "packages"
      (see [INST])

  - install_packages(
      packages: list of "Package"s of known to it types,
      environment,
    )
    Could may be even just consume regular string(s) whenever no specific
    details are needed

  - resolve_name(
      name: list of software/data names (possibly with versions?! mneh for now),
      environment: optional
    ) -> string or None
    so that top level Environment could request to install e.g. 'svn', 'pip', etc.
    We might even 'sense' if such a package is available already (thus environment)
    option.

    Might store a set of predefined resolutions (e.g. svn -> subversion,
    singularity -> singularity-container) which is  specific to distributions

    TODO future:  think how it would link into some packages requiring tune up
    of the environment or sourcing some env files specific to different distros.

- Q: could/should environment be specified at __init__ time or just memorized by
  'initiate' call, since we unlikely to re-use the same object for different environments


resource.base.Resource base class
======================

  - __init__(resource_config)
  - factory(resource_config)  (static method)
  - get_resources(config_path)  (static method)
  - get_config
  - set_config


resource.interface.environment.Environment  base class
==========================================

 - seems to not define any generic __init__
 - create(image_id) !
 - execute_command
 - ...

sub-classes (mixin Resources)
 - Ec2Instance
 - Shell
 - DockerContainer

TOL:
 - ATM it is the one deciding on "default" image to use if not provided to `create`

 - get_base_image(
    provenance_origins
   )
   should provide

   - but I foresee lots of overlap in decision making, e.g. "deduce base os"
     which we could possibly just absorb into a helper function where applicable


resource.interface.backend.Backend  base class
==================================

   Encapsulates "creation" of the client which will be used by 1 or many
   Environment objects

  __call__  Returns the client object needed to communicate with the backend service
            although initiation is done in __init__

sub-classes:   (also Resources)
 - DockerEngine
 - SingularityEngine
 - AwsSubscription
 - SshServer  ->? SshClient?

cons?
- currently initiates _client straight in __init__ and just returns it in __call__
  IMHO should be lazily created in __call__

provenance.base.Provenance
==========================

ATM provides extraction of
- get_operating_system()
   - suboptimal since we might not have anything defining base OS (e.g. spec using only conda)
- get_distributions()

sub-classes:
- ReprozipProvenance
- NicemanspecProvenance

But it seems to be not the type passed into "Distribution" which just gets a
dictionary with
['origin', 'name', 'label', 'version', 'architectures', 'components', 'date', 'suite', 'codename', 'packages']
so seems to be just as read from the spec


Bucc side
*********

Primarily came up while (re)tracing

retrace.packagemanagers.PackageManager
======================================

sub-classes:
- DpkgManager
- VCSManager
- TODO: CondaManager
- TODO: PIPManager


Glue
****

1. We should generalize `Provenance` to provide encapsulation layer on top of our
'spec' into which we should import others (e.g. ReproZip, Trig, ...).  Those are
inherently "not complete", so we should just strive to provide closest estimation
during import (e.g. from origin, codename, components, architectures -> origins).  Although would
be somewhat circular, since from the origins we need to choose the base OS later on,
it would be beneficial since original description is not complete.

2. Provenance should provide primarily a representation of the environment. So it
should be just a "model"

- origins:  list of origin objects
- packages:  list of packages associated with various origins
- other_files: list of files which did not find association with any package

and additional meta-information such as

- version:   version of our spec
- original_spec:
  - type  (e.g. reprozip)
  - version (e.g. 0.8)

Later we need to decide on specification of the 'execution' and environment
variables

3. Provenance model specs should lie close to the "Distribution" and "Manager"
   parts to simplify their use.



API commands
------------

create
======

- gets the spec but disregards it ATM and relies on image_id to be provided
  in cmdline or just to have Environment decide on which one to use.

  - our "spec ATM does not "support" any Environment-specific image specification
    - Q1:  should it be able to???  We do might want to allow for that although
      generally should figure it out from the spec list of origins
    - A1: may be we could allow for "origin" definitions which would provide
      those specs, e.g.
      {name: docker-0, type: docker-image, image: neurodebian:nd16.04, hub: whateverdockerhub, backend-specific: True}
      {name: singularity-1, type: singularity-image, hub: somesingularityhub, image: neurodebian:nd16.04, backend-specific: True}

      `backend-specific` option to state that not needed to be satisfied if backend
      not matching?

  - given the spec/provenance something should analyze/decide on what should be
    the base "image"


Observations
------------

- Some distributions (e.g. NeuroDebian) do not need custom invocation for
  install_packages.  Moreover all packages of e.g. dpkg type should better be
  passed to be installed at the same time because they might depend on each other
  although coming from different origins/Distributions.  So install_packages
  of NeuroDebian should do nothing (may be just verify that packages were installed)
  and rely on Debian/Ubuntu distribution to install them.

- That implies we might need some kind of ordering of those known types
  Debian -> NeuroDebian -> conda -> pip/pypi
  Debian -> vcs

- "down the chain" "Distribution" should instruct base to install needed tools
  ( VCS -> git or svn, pypi -> pip)

  [INST] Theoretically initiate could/should do it but it must not be aware of the base
  environment "Distribution".  So there should be some translation layer.

       Environment.install_packages(package_names, type=None)

  if type is None, should be chosen based on the Distribution, or possibly even
  go through some kind of chain of known/registered distributions


Bucc's RF idea
==============

Actors
------

- Traceable
  .identify_packages(files) -> packages, loose_files

- Provisionable
  .initiate(specification)
  .install_packages

- Tracer
  (acts upon Traceable things to harvest env spec given an environment and a list of files)
  - DebTracer

- Creator

- Distribution
  - DebianDistribution(Traceable, Provisionable)
  - UbuntuDistribution(Traceable, Provisionable)
  - NeuroDebianDistribution(Traceable, Provisionable)
     - well -- could be traced as any other DebianDistribution BUT it is not
       'standalone' so just might need to be provisioned only on top of another
     - while preparing Debian-based "distributions" we will group them based on
       origin (and/or) label (e.g. if label is different from origin)
  - Conda
  - Docker


DataModels
----------

- Package
  .origins

- Origin

- Spec    # Generic class which would also be "YAMLable", i.e. we could easily dump/load from .yml
  - Provenance(Spec)
    .files  [!!str] # just loose files... we might actually bring it under 'Files' Distribution as of the last resort
    .distributions [!!DistributionSpec]
    .runs [!!RunSpec]
    ...
  - DistributionSpec(Spec)
    .packages  [!!PackageSpec]
    - DebDistributionSpec(DistributionSpec)
      +? .system
      +? .architecture
      + .sources [!!AptSourceSpec]
      .packages  [!!DebPackageSpec]
  - RunSpec
  - AptSourceSpec(Spec)
    .name
    .component
    .archive
    .architecture
    .origin
    .label
    ...
  - PackageSpec(Spec)
  - DebPackageSpec(PackageSpec)
    .name
    .version
    .versions  [!!DebPackageAptVersionSpec]
  - DebPackageAptVersionSpec(Spec):
    version: [!!ids to point to .sources]
  - VCSPackageSpec(Spec)
    .path
    - GitPackageSpec(VCSPackageSpec)
      .


distribution: !include simple_workflow.yaml
runs:
  -

DISTRIBUTUONS
-------------

I think we can't escape those.  They would allow for nicer groupping and avoid
pulling terms by the ears... e.g.

# for now just inheriting ideas from reprozip but we might RF it to expand to
# support alternative specs (BIDS-apps, scritran's gears etc)

version: # our spec version
runs:  # to be discussed but it will provide ENV variables which will be used to establish env where retracing is done!
input_outputs:
other_files:

# here we expand
distributions:
 deb:  # just the one which uses deb (and apt and dpkg)
  sources:  # what now is origins. do not like origins -- clashes with "origin" and ppl know about apt/sources
  -
  packages:  # not even sure if we should point from which apt_sources was available
  # names might not be unique -- multiarch
  - name: ...
    version: ...
    versions: # we could still explicitly list them the same way we do for origins ATM
    - version:
      sources:
 git:
  # here might be git-specific options, e.g. some credentials or whatnot
  packages:
  - path:
    hexsha:
 svn:
  # might even have some "root" one
  packages:

 conda:
 - path: /path/conda1
   build: ...
   packages:
   -
 - path: /path/conda2
   build: ...
   packages:
   -


overall for distributions

distributions:
 TYPE:  # deb,git,svn
   LIST (list) OR A SINGLE entry (associative) of that type
    packages:
     LIST of either full *Package entries or sugarings (e.g. name=version)


Resources images
~~~~~~~~~~~~~~~~
Well -- we will use some as environments where any given spec is "implemented".
BUT we could also support resources being listed as 'packages', possibly even without
directly associated files (suchas in the case with docker):

docker:
 # could be some specific to it settings, e.g. "hubs" similar to "apt sources"
 packages:
 - image: bids/qa
   tag: latest
   id: afe...
 - "bids/cpac:latest"  # sugaring -- ideally we should use in sugarings native syntax
                       # thus wrapping here into string explicitly
   # TODO -- review docker-compose syntax to what degree we need to implement it
   #   our use cases aren't service oriented, so all the ports mapping etc is not
   #   what we really need
singularity:
 packages:
 - image: /path/sing_image.img
   md5: ...
   sha1: ...

so that in theory we could 'trace' execution "into" containers and/or just spec
commands which will use them (even if commands would fetch them automagically imho
this would be beneficial).  Corresponding "packages" then would need to have access
to that resource type backend

Sugarings
~~~~~~~~~

For packages, we should allow some sugaring in specs to facilitate entry by humans, e.g.
packages (allowing for mixing):

 - python-mvpa2=2.6.0  # may be borrow from pip for = to be non-strict, and == strict?
 - name: python-nibabel

those sugarings would be type dependent, e.g. here NAME=VERSION and in GIT, PATH=URL@treeish, etc

git:
 - /opt/niceman=http://github.com/repronim/niceman@1.0.0

then normalization would unroll those into full fledged specs