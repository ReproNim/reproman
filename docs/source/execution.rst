.. _execution:

Execution on Resources
**********************

Once a resource is present in your inventory (see :ref:`Managing
resources <manage>`), ReproMan provides a few ways to execute command(s)
on the resource. The first is to request an interactive shell for a
resource with :ref:`reproman login <man_reproman-login>`. Another is to
use :ref:`reproman execute <man_reproman-execute>`, which is suitable
for running one-off commands on the resource (though, as its manpage
indicates, it's capable of a bit more). To some degree, you can think of
``login`` and ``execute`` as analogous to ``ssh HOST`` and ``ssh HOST
COMMAND``, respectively, where the ReproMan variants provide a common
interface across resource types.

The final way to execute a command is :ref:`reproman run
<man_reproman-run>`.


Run
===

.. _rr-tasks:

``reproman run`` is concerned with running "jobs" on remote resources. It is executed from the *local* machine and handles three high-level tasks:

  1. **Prepare**: Move data to the remote resource and set up the execution environment.
  2. **Execute Job**: Submit the job to a batch system or run the command directly.
  3. **Collect**: Gather results and finalize the workflow, including retrieving outputs, collecting metadata and logs, and bringing everything together locally to complete the full workflow.


.. _rr-refex:

Reference example
-----------------

Let's first establish a simple example that we can reference as we cover
some of the details. In a terminal, we're visiting a `DataLad`_ dataset
where the working tree looks like this::

  .
  |-- clean.py
  `-- data
      |-- f0.csv -> ../.git/annex/objects/[...]
      `-- f1.csv -> ../.git/annex/objects/[...]

The ``clean.py`` script takes two positional arguments (e.g., ``./clean.py
data/f0.csv cleaned/f0.csv``), where the first is a data file to process
and the second is a path to write the output (creating directories if
necessary).

Choosing an orchestrator
------------------------

Before running a command, we need to decide on an orchestrator. The
orchestrator is responsible for the first and third :ref:`tasks above
<rr-tasks>`, preparing the remote and collecting the results. The complete
set of orchestrators, accompanied by descriptions, can be seen by
calling ``reproman run --list=orchestrators``.

.. note::

   Although DataLad is not a strict requirement, having it installed on
   at least the local machine is strongly recommended, and without it
   only a limited set of functionality is available. If you are new to
   DataLad, consider reading the `DataLad handbook`_.

The main orchestrator choices are ``datalad-pair``,
``datalad-pair-run``, and ``datalad-local-run``. If the remote has
DataLad available, you should go with one of the ``datalad-pair*`` orchestrators.
These will sync your local dataset with a dataset on the remote machine
(using `datalad push`_), creating one if it doesn't already exist
(using `datalad create-sibling`_).

``datalad-pair`` differs from the ``datalad-*-run`` orchestrators in the
way it captures results. After execution has completed, ``datalad-pair``
commits the result *on the remote* via DataLad. On fetch, it will pull
that commit down with `datalad update`_. Outputs (specified via
``--outputs`` or as a job parameter) are retrieved with `datalad get`_.

``datalad-pair-run`` and ``datalad-local-run``, on the other hand,
determine a list of output files based on modification times and
packages these files in a tarball. (This approach is inspired by
`datalad-htcondor`_.) On fetch, this tarball is downloaded locally and
used to create a `datalad run`_ commit in the *local* repository.

There is one more orchestrator, ``datalad-no-remote``, that is designed
to work only with a local shell resource. It is similar to
``datalad-pair``, except that the command is executed in the same
directory from which ``reproman run`` is invoked.

Revisiting :ref:`our concrete example <rr-refex>` and assuming we have
an SSH resource named "foo" in our inventory, here's how we could
specify that the ``datalad-pair-run`` orchestrator should be used::

  $ reproman run --resource foo \
    --orc datalad-pair-run --input data/f0.csv \
    ./clean.py data/f0.csv cleaned/f0.csv

Notice that in addition to the orchestrator, we specify the input file
that needs to be available on the remote. This is only necessary for
files that are tracked by git-annex. Files tracked by Git do not need to
be declared as inputs because the same revision of the dataset is
checked out on the remote.

.. warning::

   The orchestration with DataLad datasets is work in progress, with
   some rough edges. You might end up in a state that ReproMan doesn't
   know how to sync. Please report any issues you encounter on the
   `issue tracker <https://github.com/ReproNim/reproman/issues/>`_ .


.. _rr-sub:

Choosing a submitter
--------------------

Another, easier decision is which submitter to use. This comes down to
which, if any, batch system your remote resource supports. The currently
available options are ``pbs``, ``condor``, or ``local``. With ``local``,
the job is executed directly through ``sh`` rather than submitted to a
batch system.

Our last example invocation could be extended to use Condor like so::

  $ reproman run --resource foo \
     --sub condor \
     --orc datalad-pair-run --input data/f0.csv \
    ./clean.py data/f0.csv cleaned/f0.csv

Note that which batch systems are currently supported is mostly a matter
of which systems ReproMan developers currently have at their disposal.
If you would like to add support for your system (or have experience
with more general approach like DRMAA_), we'd welcome help in this area.


Detached jobs
-------------

By default, when a ``run`` command is executed, it submits the job,
registers it locally, and exits. The registered jobs can be viewed and
managed with :ref:`reproman jobs <man_reproman-jobs>`. To list all jobs,
run ``reproman jobs`` without any arguments. To fetch a completed job
back into the local dataset, call ``reproman jobs NAME``, where ``NAME``
is a substring of the job ID that uniquely identifies the job.

In cases where you prefer ``run`` to stay attached and fetch the job
when it is finished, pass the ``--follow`` argument to ``reproman run``.


Concurrent subjobs
------------------

If you're submitting a job to a batch system, it's likely that you want
to submit concurrent subjobs. To continue with the :ref:`toy example
<rr-refex>` from above, you'd want to have two jobs, each one running
``clean.py`` on a different input file.

``reproman run`` has two options for specifying subjobs:
``--batch-parameter`` and ``--batch-spec``. The first can work for
simple cases, like our example::

  $ reproman run --resource foo --sub condor --orc datalad-pair-run \
    --batch-parameter name=f0,f1 \
    --input 'data/{p[name]}.csv'  \
    ./clean.py data/{p[name]}.csv cleaned/{p[name]}.csv

A subjob will be created for each ``name`` value, with any ``{p[name]}``
field in the input, output, and command strings formatted with the
value. In this case, the two commands executed on the remote would be

::

  ./clean.py data/f0.csv cleaned/f0.csv
  ./clean.py data/f1.csv cleaned/f1.csv

The ``--batch-spec`` option is the more cumbersome but more flexible
counterpart to ``--batch-parameter``. Its value should point to a YAML
file that defines a series of records, each one with all of the
parameters for a single subjob command. The equivalent of
``--batch-parameter name=f0,f1`` would be a YAML file with the following
content::

   - name: f0
   - name: f1

.. warning::

   When there is more than one subjob, ``*-run`` orchestrators do not
   create a valid run commit. Specifically, `datalad rerun`_ could not
   be used to rerun the commit on the local machine because the values
   for the inputs, outputs, and command do not correspond to concrete
   values. This is an unresolved issue, but at this point the commit
   should be considered as a way to capture the information about the
   remote command execution---one that certainly provides more
   information than logging into the remote and running
   ``condor_submit`` yourself.


Job parameters
--------------

To define a job, ReproMan builds up a "job spec" from job parameters.
Call ``reproman run --list=parameters`` to see a list of available
parameters. The parameters can be specified within a file passed to the
``--job-spec`` option, as a key-value pair specified via the
``--job-parameter`` option, or through a dedicate command-line option.

The last option is only available for a subset of parameters, with the
intention of giving these parameters more exposure and making them
slightly more convenient to use. In the examples so far, we've only seen
job parameters in the form of a dedicated command-line argument, things
like ``--orc datalad-pair-run``. Alternatively this could be expressed
more verbosely through ``--job-parameter`` as ``--job-parameter
orchestrator=datalad-pair-run``. Or it could be contained as a top-level
key-value pair in a YAML file passed to ``--job-spec``.

.. _jp_precedence:

When a value is specified in multiple sources, the order of precedence
is the dedicated option, then the value specified via
``--job_parameters``, and finally the value contained in a
``--job-spec`` YAML file. When multiple ``--job-spec`` arguments are
given and define a conflicting key, the value from the last specified
file wins.


Captured job information
------------------------

When using any DataLad-based orchestrator, the run will ultimately be
captured as a commit in the dataset. In addition to working tree changes
that the command caused (e.g., files it generated), the commit will
include new files under a ``.reproman/jobs/<resource name>/<job ID>/``
directory. Of the files from that directory, the ones described below
are likely to be of the most interest to callers.

submit
    The batch system submit file (e.g., when the :ref:`submitter
    <rr-sub>` is ``condor``, the file passed to ``condor_submit``).

runscript
    The wrapper script called by the submit file. It runs the subjob
    command indicated by its sole command-line argument, an integer that
    represents the subjob.

std{out,err}.N
    The standard output and standard error for each subjob command. If
    subjob ``N``, ``stderr.N`` is where you should look first for more
    information.

spec.yaml
    The "job spec" mentioned in the last section. Any key that does
    *not* start with an underscore is a job parameter that can be
    specified by the caller.

    In addition to recording information about the submitted job, this
    spec can provide a starting point for future ``reproman run`` calls.
    You can copy it to a new file, tweak it as desired, and feed it in
    via ``--job-spec``. Or, instead of copying the file, you can give
    the original file to ``--job-spec`` and then :ref:`override the
    values <jp_precedence>` as needed with command-line arguments or
    later ``--job-spec`` values.


.. _DataLad: https://www.datalad.org/
.. _Datalad Handbook: http://handbook.datalad.org
.. _datalad create-sibling: https://datalad.readthedocs.io/en/latest/generated/man/datalad-create-sibling.html
.. _datalad get: https://datalad.readthedocs.io/en/latest/generated/man/datalad-get.html
.. _datalad push: https://datalad.readthedocs.io/en/latest/generated/man/datalad-push.html
.. _datalad rerun: http://docs.datalad.org/en/latest/generated/man/datalad-rerun.html
.. _datalad run: http://docs.datalad.org/en/latest/generated/man/datalad-run.html
.. _datalad update: https://datalad.readthedocs.io/en/latest/generated/man/datalad-update.html
.. _datalad-htcondor: https://github.com/datalad/datalad-htcondor

.. _DRMAA: https://en.wikipedia.org/wiki/DRMAA
