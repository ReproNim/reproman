Current hierarchy
-----------------

Matt side
*********

distribution.base.Distribution   base class
===============================

 - __init__ (provenance)
 - factory [static]  (distribution_name, provenance)
    provenance given to __init__
 - initiate (session)
 - install_packages (session)

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
  So e.g. `install_packages` should get a list of versioned packages and the `session`
  to be used to install them

  - __init__()  -- leave agnostic of the "provenance"?
     possibly provide with session to operate on? (shared state among all methods)

  - initiate(
     dist_spec: distribution portion of the specification
     session: the session to operate in
    )

    might want to do
    - necessary checks if session is compatible with this distribution and
      possibly is already satisfied (could be useful to be able to use functionality
      from trace!)
    - instruct already pre-setup session to install necessary "packages"
      (see [INST])

  - install_packages(
      packages: list of "Package"s of known to it types,
      session,
    )
    Could may be even just consume regular string(s) whenever no specific
    details are needed

  - resolve_name(
      name: list of software/data names (possibly with versions?! mneh for now),
      session: optional
    ) -> string or None
    so that top level Environment could request to install e.g. 'svn', 'pip', etc.
    We might even 'sense' if such a package is available already (thus session)
    option.

    Might store a set of predefined resolutions (e.g. svn -> subversion,
    singularity -> singularity-container) which is  specific to distributions

    TODO future:  think how it would link into some packages requiring tune up
    of the session or sourcing some env files specific to different distros.

- Q: could/should session be specified at __init__ time or just memorized by
  'initiate' call, since we unlikely to re-use the same object for different sessions


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

- Distribution(Traceable, Provisionable)
  - DebianDistribution
  - UbuntuDistribution
  - NeuroDebianDistribution
     - well -- could be traced as any other DebianDistribution BUT it is not
       'standalone' so just might need to be provisioned only on top of another
     - while preparing Debian-based "distributions" we will group them based on
       origin (and/or) label (e.g. if label is different from origin)
     - all of above might need generic common parent DebDistribution since there
       will be only a few particular aspects of them, primarily concerning
     - they all to varying degree could
         guess_apt_sources(packages) -> [!!AptSourceSpec]
       to figure out additional apt sources needed to fulfill packages list if
       we (how?) determine that it is necessary.  Could may be a generic API
         adjust_distribution_to_fulfill_packages(!!DistributionSpec, environ)
       which internally would first figure out which versions of packages are
       available in the active `environ` and see how/if it could satisfy for
       missing ones, and that is where `guess_apt_sources(packages)` would kick
       in.  BUT that is where making boundaries between Debian and NeuroDebian
       as separate distributions would hurt :-/  Unless we come up with central
       class/object "Distributions" with `.has_a_package(package)`.
  - Conda
  - Docker


DataModels
----------

Spec or Model????

- Spec    # Generic class which would also be "YAMLable", i.e. we could easily dump/load from .yml
  - RunSpec
  - Environment(Spec)
    .base   ????? # to encode information such as kernel, lsb_release of the base system?
            (LinuxBase,DockerImage,SingularityImage,AWS), i.e.
    .distributions [!!DistributionSpec]
    .files  [!!str] # just loose files... we might actually bring it under 'Files' Distribution as of the last resort
    .packages [!!PackageSpec]  # generic specs for packages which could later be assigned into distributions
    # .runs [!!RunSpec]   -- most probably will not be here! we will move them outside, and they could (optionally) point to environment spec
    ...
  - DistributionSpec(Spec)
    .packages  [!!PackageSpec]
    - DebDistributionSpec(DistributionSpec)
      +? .system
      +? .architecture
      .lsb_id        # Debian, Ubuntu (CentOS later)
      .lsb_release   # APT sources might list multiple but we could analyze or just record which one is currently used
      .lsb_codename
      + .sources [!!AptSourceSpec]
      .packages  [!!DebPackageSpec]
    - CondaSpec(Spec)
     +? .version
     +? .build
     +? .python_version
     +? .type  (anaconda, miniconda, ...)
     .packages  [!!CondaPackageSpec]
    - Docker   # happen someone runs smth like a dockerized BIDSApp.
               # We should capture availability of that image so it could be used in 'runs' scripts/commands
              # We can't provision Containers though! although optionally could detect starting container, so we could make an image and thus -- provision!
      .images [!!DockerImageSpec]
  - AptSourceSpec(Spec)
    .name
    .component
    .archive
    .architecture
    .origin
    .label
    .suite
    .codename # should we allow for custom referencing of upstairs attributes, e.g. $lsb_codename to facilitate easy manipulations?
    ...
  - PackageSpec(Spec)
  - DebPackageSpec(PackageSpec)
    .name
    .version
    .versions  [!!DebPackageAptVersionSpec]
  - CondaPackageSpec
    .name
    .version
    .build
    .manager:  conda, pip   # could be either!  so it is not per se "CondaPackage"... not sure how/where we should distinguish
  - DebPackageAptVersionSpec(Spec):
    version: [!!ids to point to .sources]
  - VCSPackageSpec(Spec)
    .path
    - GitPackageSpec(VCSPackageSpec)
      .
  - FilesPackageSpec    # some additional flexible specs to allow e.g. to accompany spec with collections of files to be deployed into env

  - LinuxBase
    . kernel
    ?. architecture

  - DockerImage
    . image
    . dockerfile   # could be specified one way or another
    # . container    # probably shouldn't be here for various reasons?


If we move runs specification outside (as probably it should) we could then
provide some semantics to include env spec within "execution specification"

environment: !include simple_workflow.yaml
runs:
  -

build_env_debian.yaml
packages:
  - name: g++
  - name: cmake


build_env_centos.yaml
packages:
  -name: gcc-c++
  -name: cmake


build_env.yaml
packages:
 include: build_env_debian.yaml
 git:
  - url: http://github.com/...


DISTRIBUTUONS
-------------

I think we can't escape those.  They would allow for nicer groupping and avoid
pulling terms by the ears... e.g.

# for now just inheriting ideas from reprozip but we might RF it to expand to
# support alternative specs (BIDS-apps, scritran's gears etc)

version:        # our spec version
base:           # possible base on top of which to operate.  Could be discovered basic LinuxBase or DockerImage or ...
 # either
 linux:
 - kernel:
  - release: 4.9.0-2-amd64
  - machine: x86_64
 # or
 docker:   # serves as a base for everything listed below so no need for list - a single entry
  image: debian:stretch  # name?repository:tag  so
distributions:  # here we expand
 deb:  # just the one which uses deb (and apt and dpkg)
  sources:  # what now is origins. do not like origins -- clashes with "origin" and ppl know about apt/sources
  -
  packages:  # not even sure if we should point from which apt_sources was available
  # names might not be unique -- multiarch
  - name: ...
    version: ...
    versions: # we could still explicitly list them the same way we do for origins ATM
     version: sources
 git:
  # here might be git-specific options, e.g. some credentials or whatnot
  packages:
  - path:
    hexsha:
 svn:
  # might even have some "root" one
  packages:

 # Tricky one since might have multiple distributions!
 conda:
 - path: /path/conda1
   build: ...
   packages:
   -
 - path: /path/conda2
   build: ...
   packages:
   -

 docker:   # to cause "docker distribution" to do   docker pull  on every image
  images:
   - repository: debian
     id: 19134a8202e7
     tag: stretch
     ?image:   debian:stretch    # alternative?
     ?digest:
     ?index:      # not sure if possible to discover ATM see http://rancher.com/comparing-four-hosted-docker-registries/ for concepts
     ?registry:   # but if we allow for specification -- might be helpful.
     ?repository: # BUT overlaps somewhat with what we should be specifying in resources!



distributions:
 deb:
  packages:
   - name: fsl
     version:
   - name: docker.io
     version:
 docker:
  images:
   - image: fsl-worker
     id: 19134a

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



Actual hierarchy
----------------

To make separation of interfaces cleaner

(active interfaces)
Tracer      - given env, outputs specs
Provisioner - given env and specs, performs installations

  Debian(Tracer, Provisioner)

Resource - base class for anything we manage within out 'inventory'
           configuration.  So shouldn't be a part of the spec although some "models" could/should be reused, e.g. for images
 Image    - a resource which could be shared, or could be instantiated (docker image, aws ec2 instance)
 Instance - an instantiation of an image which could generate sessions
            - could have state (off, on, booting, ...)
            - should be "linked" to original image (.parent?)
 Session  - active session which could execute commands, could be
            - active (connected, can run commands)
            - reenterable (e.g. session of a running docker container)
              - could actually have multiple entries (or we could separate that out into separate property)
              - should retain possibly changed env, so we should store it after each command exec or just rely on .set_envvar and .source_file?
            - persistent (not only reenterable but stateful -- the shell doesn't terminate as with screen or VNC within any other session)
            - should be linked back to original resource (instance, image) (.parent?)

            .run(cmd, track_env=False)

            .set_envvar(var, value, session_only=False, format=False)
               - `session_only` is to store only for this session only as to facilitate dockers ARG.
                 If False (default), change should be persistent and reflected in running commands there
                 later and/or generated image
               - `format` is to allow format using already existing variables  (e.g. PATH=/blah:{PATH})
               - I don't think we need to expose that ARG handling from cmdline API as docker does at this time/level
               - internally should maintain two versions I guess (session_only and overall)
                 - idea: could generalize by adding `space=None` argument which would instruct within which
                   env space it would be stored.  E.g. space=`session` would be identical to session_only.
                   But becomes somewhat incongruent since after this one is done we want the one without any spaces

                   Might be difficult/cumbersome to make it generic across all sessions, may be only via
                   generating (e.g. /root/.niceman/spaces/SPACE) and sourcing them for every command run in
                   case of docker since we can't otherwise augment env.  Having a single "session_only" makes
                   it easi(er)
            .set_envvars(vars:dict, update=True, ...) - sugaring on top to pass entire dict and update or overload entirely
            .get_envvars(session=False) -> dict
               - with `session` True, would return also

            ???.set_runner(cmd, space=None) -- might go away
               - set the command which would be used to run each command, e.g. `eatmydata` ??? or should not be as generic...?
                 may be we need some kind of execution profiles (again -- `space`)
                  so I could say ".set_envvar('DEBIAN_FRONTEND', 'noninteractive', space='deb'); .set_runner('eatmydata', space='deb')"
               - might be avoided if we create a shim for commands we care to run through `eatmydata` and then
                  `.copy_files_into('shims/', '/usr/local/niceman/bootstrap/shims')`
                  `.set_envvar('PATH', '/usr/local/niceman/bootstrap/shims:{PATH}', space='apt')`
                 This way we could control via spaces where we want eatmydata assistance and for which tools
               - could be default, per distribution in some kind of "prepare_for_deploy" step -- which packages to install and what to set for the env
            .source_file(filename, args=[])
               - needed to activate conda/pip/modules envs
            .copy_files_into(src, dest, ..., permissions=?, recursive=False)
            # if to aim for better coverage of Dockerfile "API".  Could be made supported for others (singularity, ssh, localhost)
            .set_user(user)
            .set_entry_command(cmd)

            Batched one:
            - .finalize_batch()  -- if was ran in batch mode

Backends (docker, localhost, aws-ec2) - generate/manipulate image/instance/sessions
   - depending on the backend, `session` might need to be generated directly (e.g. localhost)
     or would need to be done from Image (singularity) or from Instance (docker).
     Some (schroot) could go directly into instance but allow for image (tarball)

   .instantiate(image) -> instance (docker start)
   .start_session(instance or image, session_spec=None, options=None, background=False, batched=False)
    - in case of batched session, returned Session should have '.finalize_batch'?
    - if it is an interactive with tty -- would not return I guess since it would be active?
    - `options` are to provide backend specific options to session (the same below for build_image for image, etc)
   .join_session(session)
   .snapshot_image(session or instance, image_name) -> image_instance_spec
   .build_image(env_spec, image_name, target_image_spec=None, options=None, batched=False) -> image_instance_spec  [not avail for localhost]
    - in case of batched,
         docker and singularity could use their BatchedSession
         to generate Dockerfile or Singularity.def which they would pass to their 'build'
         and generate an image
      in case of not batched, they
        - .instantiate first
        - .start_session
        - run the commands
        - .snapshot_image
    - image_spec
   .stop_session()
    .run(..., rm=False)  -- sugaring which chains things up if needed or directly calls if available applicable

So "features"(passive)/interfaces
 Instantiable? (DockerImage, but not SingularityImage)
 CanStartSession (SinularityImage)

Depending on the backend

-
  - base/ -- base classes definitions etc
    - models  - would provide base definitions and functionality for all the specs etc
  - cmdline/ -- cmdline helpers
  - interface/ -- interface functionality
    - create -- out of spec create a resource (image, instance, ...) [internally would be create_instance, install, .snapshot]
    - install -- (might meld with create) given an existing resource (image, instance, ...) perform installation actions within
    - retrace -- given a resource and (possibly optional) list of files, create spec describing it
    - run -- given a resource or spec, and a command, get a session and run the command
  - distributions/ - aggregate everything related to the distribution within
                     (so should absorb majority of retrace. The "retrace" controller code should go to retrace.py for now)
    - base -- base classes
    - base_vcs -- base classes for VCSs
    - debian -- definitions for packages, distribution spec, Tracer/Provisioner
    - conda
    - docker
    - git
    - svn
  - formats/ - serialized (files) representations
    - base -- base classes
    - niceman -- will be pretty much straight dump of the model BUT there could be others
    - reprozip
    - trig
    - NEW: human  ;)
    - NEW: neurodocker-like
    - examples/  (move from top level)
  - resource[s]/ -- computational resources... ????  RF into ... backends!  they will provide resources though!
    - aws_ec2
    - docker
    - singularity
  - support/ - misc stuff
  - tests/ - top level tests
  - ui/  - ui related stuff


Registry of (external) resources to serve as the bases
------------------------------------------------------

Yarik hates maintaining lists of things manually ;)

When a new instance or image is asked to be built based on spec, we need to
figure out the base.  E.g. which docker image to use.  One approach, as taken
by e.g. reprozip, manually curate such a list, and hardcode for each 'release'
the one to use.

More flexible (in you's mind) would be to allow to create such a list of external
resources by e.g.  pulling all the images available for docker, "tracing" their
features (lsb_release, apt sources), and recording that information as an
available resource (they are available upon pull).  Then during analysis for
which base to choose -- check available images about which "fits" the best e.g.
base on lsb_release info and apt line entries (origin, date) in case there are
multiple.

Problem -- if there is way too many, and some are "derived" images so their
lsb/apt would be good but they wouldn't be "bare".  So we should annotate that only
some resources are "base", and then only if none found, we could ask if user
wants to try to use some other available or request update of the resources from
external sources until satisfying one is found.

It might need to be either a separate registry of resources (which we could
potentially ship), or somehow tagged within a bigger collection.

Another


Resources
---------

? .type to identify different "types" of resources available

- backend
- image
- container
- session

but how to differ types?  in theory each image/container is associated with a
backend, so we could just add those for each resource (where not a backend itself)

Resource "management" could may be made "transparent" at the level of manipulating
their Python objects

- each class deriving from a resource could have .RESOURCE_TYPE field
- creating a new resource should place it into registry.
  E.g. if we create a new Container of some type, or an image, it would
  automatically be added to registry. Starting a session -- adds to registry.
  Stopping session -- removes from registry.  So overall we need

  - create (start)
  - delete (stop)
  - get_status  -- we already have it reported in ls but seems to differ from
               the one in inventory.json
  - validate  -- to check if resource entry is still valid (image or container
                  still exists, etc)