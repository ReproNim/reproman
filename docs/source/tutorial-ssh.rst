.. _tutorial-ssh:

Tutorial: SSH Resource Workflows
*********************************

This tutorial walks you through ReproMan workflows using SSH resources, from simple command execution to complex data analysis.
We'll start with a basic hello-world example, then progress to processing neuroimaging data.

This tutorial demonstrates ReproMan's power in creating reproducible, traceable computational workflows across SSH-accessible computing environments.

Overview
========

We'll cover two workflows:

**Part 1: Hello World Example**
1. Create a ReproMan SSH resource  
2. Execute a simple command remotely
3. Fetch and examine results

**Part 2: Dataset Analysis Example**
1. Set up a DataLad dataset with input data
2. Execute MRIQC quality control analysis remotely  
3. Collect and examine results with full provenance

Prerequisites
=============

- ReproMan installed (``pip install reproman``) 
- Access to a remote server via SSH
- For Part 2: DataLad support (``pip install 'reproman[full]'``)

Part 1: Hello World Example
============================

Step 1: Create an SSH Resource
-------------------------------

First, let's add an SSH resource to ReproMan's inventory. Replace ``your-server.edu`` with your actual server::

  reproman create myserver --resource-type ssh --backend-parameters host=your-server.edu

Verify the resource was created::

  reproman ls --refresh

.. note::

   The ``--refresh`` flag is needed to check the current status of resources. Without it, you'll only see cached status information.

You should see output similar to::

  RESOURCE NAME        TYPE                 ID                  STATUS
  -------------        ----                 --                  ------
  myserver             ssh                  1a23b456-789c-      ONLINE

Step 2: Execute a Simple Command
---------------------------------

Let's start with a simple test to verify our setup works. Create a working directory and run a basic command::

  mkdir -p hello-world
  cd hello-world
  
  reproman run --resource myserver \
    --sub local \
    --orc plain \
    --output results \
    sh -c 'mkdir -p results && echo "Hello from ReproMan on $(hostname)" > results/hello.txt'


Step 3: Fetch Results
---------------------

The job will execute on the remote. To check status and fetch results::

  # Check job status and get job ID
  reproman jobs

  # Fetch results for completed job (replace JOB_ID with actual ID)
  reproman jobs JOB_ID

When you run ``reproman jobs JOB_ID``, ReproMan will automatically:

- Fetch the output files from the remote to your local working directory
- Display job information and logs  
- Unregister the completed job

You should now see the results locally::

  cat results/hello.txt

.. note::

   ReproMan creates a working directory on the remote resource automatically. By default, it uses ``~/.reproman/run-root`` on the remote. You can verify the file exists there with ``reproman login myserver``.

Part 2: Dataset Analysis Example  
=================================

Now let's try a more realistic example with DataLad dataset management and neuroimaging analysis.

Step 1: Set Up the Analysis Dataset
------------------------------------

Create a new DataLad dataset for our analysis::

  # Create dataset for MRIQC quality control results
  datalad create -d demo-mriqc -c text2git
  cd demo-mriqc

Install input data (using a demo BIDS dataset)::

  # TODO does this have to be fetched locally? i think no?
  # Install demo neuroimaging dataset  
  datalad install -d . -s https://github.com/ReproNim/ds000003-demo sourcedata/raw


Set up working directory to be ignored::

  # TODO oneline with datalad run
  echo "workdir/" > .gitignore
  datalad save -m "Ignore processing workdir" .gitignore

Step 2: Execute Analysis with DataLad Integration
-------------------------------------------------

For full provenance tracking with DataLad::

  reproman run --resource myserver \
    --sub local \
    --orc datalad-pair-run \
    --input sourcedata/raw \
    --output . \
    bash -c 'podman run --rm -v "$(pwd):/work:rw" nipreps/mriqc:latest /work/sourcedata/raw /work/results participant group --participant-label 02'

Step 3: Monitor Execution
-------------------------

ReproMan jobs run in detached mode by default. Monitor progress::

  # List all jobs
  reproman jobs

  # Check specific job status (replace JOB_ID with actual ID)
  reproman jobs JOB_ID

  # Fetch completed job results
  reproman jobs JOB_ID --fetch

For attached execution (wait for completion)::

  reproman run --resource myserver --follow \
    [... rest of command ...]

Step 4: Examine Results and Provenance
--------------------------------------

Once the job completes, examine what was captured::

  # View the provenance record
  git log --oneline -1

  # Look at captured job information
  ls .reproman/jobs/myserver/

  # View job specification
  cat .reproman/jobs/myserver/JOB_ID/spec.yaml

  # Check MRIQC outputs
  ls -la results/

The DataLad orchestrators create rich provenance records::

  # View the detailed run record
  git show --stat

  # See what files were modified/added
  git show --name-status
