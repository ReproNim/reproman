.. _manage:

Managing resources
******************

ReproMan works with a set of known resources, such as SSH-accessible
remote machines and local Docker containers. New resources can be added
with :ref:`reproman create <man_reproman-create>`. The following, for
example, creates a new ``ssh`` resource named "foo"::

  $ reproman create foo --resource-type ssh --backend-parameters host=foo

This takes advantage of the details about this host being defined in an
``ssh_config`` configuration file. If a host were not, you could specify
details like the user and port as additional key-value pairs to
``--backend-parameters``. To see the full list of the available resource
types and the associated backend parameters, call :ref:`reproman
backend-parameters <man_reproman-backend-parameters>`.

Creating a resource adds it to ReproMan's inventory of resources. You
can inspect resources in ReproMan's inventory with :ref:`reproman ls
<man_reproman-ls>`::

  $ reproman ls --refresh
  RESOURCE NAME        TYPE                 ID                  STATUS
  -------------        ----                 --                  ------
  buster               docker-container     b29085a427de1efedb6 running
  foo                  ssh                  7a06ae6b-8097-4c59- ONLINE

The output above includes an entry for the SSH resource create above,
"foo", along with a resource for a Docker container.

While most of the ReproMan subcommands have an argument that specifies
which resource to operate on (e.g., the resource to :ref:`execute
<execute>` a command on), there are only few more dedicated subcommands
for managing resources: :ref:`stop <man_reproman-stop>`, :ref:`start
<man_reproman-start>`, and :ref:`delete <man_reproman-delete>`. Together
``stop`` and ``start`` provide a way to suspend and restart a resource
such as a Docker container or an AWS EC2 instance. For resource types
where suspending the resource doesn't make sense (e.g., for an ``ssh``
resource), calling ``start`` or ``stop`` will simply tell you the action
isn't supported.

``delete`` is the opposite of ``create``. Calling ``reproman delete
foo`` would delete the remove the resource created above from ReproMan's
inventory.
