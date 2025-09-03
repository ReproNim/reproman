.. _overview:

Overview
********

ReproMan simplifies creation and management of computational :ref:`resources <glossary>` for reproducible research. It provides tools for managing resources and running analyses with full :ref:`execution <execution>` provenance tracking.

What ReproMan Does
==================

ReproMan addresses key challenges in computational research by managing two core concepts:

- **Resources**: Computing targets like local Docker containers, remote SSH servers, or cloud instances
- **Execution**: Running analyses on these resources with comprehensive provenance tracking and environment management

ReproMan acts as a unified interface across different resource types, allowing you to:

- Create and manage computational resources consistently
- Execute analyses with automatic provenance capture and environment setup
- Track computational workflows for full reproducibility

What ReproMan Provides
======================

Provenance
----------

Every execution is automatically tracked with detailed metadata including:

- Input and output files
- Execution environment details
- Command parameters and batch system information
- Complete audit trail for reproducibility

Reproducibility
---------------

ReproMan captures sufficient information to:

- Recreate computational environments
- Rerun analyses with identical conditions
- Share reproducible workflows with collaborators
- Validate research results

Resource Management
-------------------

Unified interface for diverse computing resources:

- Local environments (Docker containers, shell)
- Remote systems (SSH, HPC clusters)
- Cloud platforms (AWS, with batch processing support)
- Consistent commands across all resource types

Data Movement and Version Control
----------------------------------

ReproMan orchestrates data movement to and from remote resources, handling:

- Input data transfer to execution environments
- Output collection and retrieval after processing
- Integration with `DataLad`_ for comprehensive data management

This provides a complete solution for reproducible computational research workflows.

.. _DataLad: https://www.datalad.org/
