.. -*- mode: rst; fill-column: 79; indent-tabs-mode: nil -*-
.. vi: set ft=rst sts=4 ts=4 sw=4 et tw=79:
  ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###
  #
  #   See COPYING file distributed along with the reproman package for the
  #   copyright and license terms.
  #
  ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###

.. _chap_glossary:

********
Glossary
********

ReproMan uses terminology which is collated from various technologies. This
glossary provides definitions for terms used in the ReproMan documentation
and API, and provides additional references where to seek more information

.. glossary::
  :sorted:

  container
    A lightweight, portable runtime environment that packages an application with its dependencies. ReproMan supports Docker_ and Singularity_ containers for reproducible execution across different systems.

  package
    A software component or library that can be installed and managed within a computational environment. ReproMan can track and reproduce package installations across different resource types.

  environment
    A configured computational context with specific software, libraries, and settings. ReproMan creates and manages environments on various resources to ensure reproducible execution of scientific workflows.

  virtual machine
    A complete operating system running on virtualized hardware, providing strong isolation and reproducibility. ReproMan can create and manage VMs on cloud platforms like AWS.

  cloud instance
    A virtual server running on cloud infrastructure (such as AWS EC2) that can be dynamically created, configured, and destroyed. ReproMan uses cloud instances to provide scalable computational resources.

  resource
    A computational target where ReproMan can execute commands and manage environments. Resources represent different types of compute infrastructure including local machines, virtual machines, cloud instances, and containers.

  orchestrator
    A component responsible for staging input data and handling results before and after running commands on resources. Examples include plain orchestrators for simple tasks and DataLad-based orchestrators for reproducible workflows.

  submitter
    A component that handles the actual submission of jobs to execution systems on a resource. Submitters manage different job scheduling systems such as local execution, batch systems (SLURM, PBS), or container orchestration platforms.

.. _Docker: http://docker.io
.. _Singularity: http://singularity.lbl.gov
