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
  (acts upon Traceable things to harvest env spec)
- Creator


- Distribution
  - DebianDistribution(Traceable, Provisionable)


DataModels
----------

- Package
  .origins

- Origin

- Specification
  - DistributionSpecification
    .origins
    .packages
    .other_files
  - RunSpecification


distribution: !include simple_workflow.yaml
runs:
  -


