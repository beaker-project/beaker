Execution environment for tasks
===============================

This sections describes the commands and environment variables which are 
available in the execution environment for tasks. At a bare minimum, a task 
should use :program:`rhts-report-result` to report a Pass or Fail result when 
it finishes.

The `BeakerLib <https://github.com/beakerlib/beakerlib>`_ shell library provides 
many convenience functions on top of these commands, including functions to 
structure complicated tasks into separate phases.

Commands
~~~~~~~~

The following commands are available in ``PATH`` when a task is executed. The 
task can use these to interact with Beaker.

These commands originated in the Red Hat Test System (RHTS), the precursor to 
Beaker, which is why their names begin with the prefix "rhts-".

rhts-abort
----------

.. program:: rhts-abort

::

    rhts-abort -t <type>

Aborts the current recipe, recipe set, or job. A setup task might call this if 
it detects a failure that will prevent the rest of the recipe from running.

.. option:: -t <type>

   Valid values are ``recipe``, ``recipeset``, or ``job``. Abort the recipe, 
   the containing recipe set, or the entire job. This option is required.

rhts-backup
-----------

.. program:: rhts-backup

::

    rhts-backup <file> [<file> ...]

Copies the given files or directories to a temporary storage area for the 
duration of the task. The files will be copied back to their original location 
at the end of the task, using the corresponding :program:`rhts-restore` 
program.

For example, a task which needs to modify ``/etc/hosts`` could back it up 
before modifying it:

.. code-block:: bash

   rhts-backup /etc/hosts
   echo "127.0.0.1 testing-bad-values" >/etc/hosts
   # test some more things here...

When the task finishes, :program:`rhts-restore` copies the original version of 
``/etc/hosts`` back, leaving the system in a clean state for the next task.

rhts-power
----------

.. program:: rhts-power

::

    rhts-power <fqdn> <action>

Sends a power command to another system in the recipe set.

.. describe:: <fqdn>

   FQDN of the system to be power-controlled.

.. describe:: <action>

   Power command to send. These correspond to the power commands available in 
   Beaker. Valid values are ``on``, ``off``, ``reboot``, and ``interrupt``.

.. _rhts-reboot:

rhts-reboot
-----------

.. program:: rhts-reboot

Saves the harness state, and then reboots the system. Tasks should use this 
command instead of the conventional :program:`reboot` command.

The task script should test the :envvar:`REBOOTCOUNT` environment variable 
before rebooting, to avoid infinite loops. For example::

    if [ "$REBOOTCOUNT" -eq 0 ] ; then
        # do some setup work here
        rhts-reboot
    fi
    # do the real work here

.. _rhts-report-result:

rhts-report-result
------------------

.. program:: rhts-report-result

::

    rhts-report-result <testname> <result> <outputfile> [<metric>]

Reports a Pass or Fail result to Beaker. A task can report multiple results 
(for example, for different phases or cases) but it should report at least one 
result.

.. describe:: <testname>

   Test name for the result being reported. By convention the result of the 
   entire task is reported as ``$TEST``, and any individual phases or cases 
   within the task are reported as a path underneath ``$TEST`` (for example, 
   ``$TEST/setup``, ``$TEST/test-case-5``). However Beaker accepts any string 
   for the test name.

.. describe:: <result>

   Result to report. Valid values are ``PASS``, ``WARN``, ``FAIL``, or
   ``SKIP``.

.. describe:: <outputfile>

   File name of the captured output or logging relevant to this result. The 
   file will be uploaded to Beaker and made available alongside the reported 
   result in Beaker's interface.

.. describe:: <metric>

   Optional integer "score" or "metric" to be shown alongside this result. 
   Beaker assigns no meaning to this score, the task can use it for any 
   purpose. Some example uses include: the score from a performance test run, 
   the number of test cases executed, or the exit status of a failing command.

rhts-restore
------------

.. program:: rhts-restore

Restores files which were previously backed up using :program:`rhts-backup`. 
This command is run automatically when a task finishes, there is normally no 
need to invoke it explicitly in the task.

rhts-run-simple-test
--------------------

.. program:: rhts-run-simple-test

::

    rhts-run-simple-test [-u <user>] <testname> <command>

Runs the given command, with output redirected to ``$OUTPUTFILE``, and reports 
a Pass or Fail result according to the exit status of the command. If you have 
another program or script which does the real work for the task (for example, 
a test suite runner), you can use :program:`rhts-run-simple-test` as a wrapper 
around it.

.. option:: -u <user>

   Run the command as *user*.

.. describe:: <testname>

   Test name to use when reporting the result to Beaker. See 
   :program:`rhts-report-result`.

.. describe:: <command>

   Command to run. Note that shell word splitting is applied to *command*, so 
   any additional arguments should be passed as a single word.

rhts-submit-log
---------------

.. program:: rhts-submit-log

::

    rhts-submit-log -l <file>

Uploads a log file to Beaker. The file will be available in the Beaker results 
for the current task.

.. _rhts-sync-block:

rhts-sync-block
---------------

.. program:: rhts-sync-block

::

    rhts-sync-block -s <state> [--timeout <timeout>] [--any] <fqdn> [<fqdn> ...]

Blocks until the given systems in this recipe set have reached a certain state. 
Use this command, along with :program:`rhts-sync-set`, to synchronize between 
systems in a multihost recipe set.

Refer to :doc:`multihost` for a more detailed guide.

.. option:: -s <state>

   Wait for the given state. If this option is repeated, the command will 
   return when any of the states has been reached. This option is required.

.. option:: --timeout <timeout>

   Return a non-zero exit status after *timeout* seconds if the state has
   not been reached. By default no timeout is enforced and the command will
   block until either the given state is reached on all specified systems
   or the recipe is aborted by the local or external watchdog.

.. option:: --any

   Return when any of the systems has reached the given state. By default, this 
   command blocks until *all* systems have reached the state.

.. describe:: <fqdn> [<fqdn> ...]

   FQDN of the systems to wait for. At least one FQDN must be given. Use the 
   role environment variables to determine which FQDNs to pass.

.. _rhts-sync-set:

rhts-sync-set
-------------

.. program:: rhts-sync-set

::

    rhts-sync-set -s <state>

Sets the given state for this system. Other systems in the recipe set can use 
:program:`rhts-sync-block` to wait for a state to be set on other systems.

States are scoped to the current task. That is, states set by the current task 
will have no effect in subsequent tasks. You can use the matching commands 
:program:`rhts-recipe-sync-set` and :program:`rhts-recipe-sync-block` to set 
and wait for states that are global for the recipe instead.

Internal commands
-----------------

The following commands are used internally by the harness and should not be 
invoked by tasks directly:

* :program:`rhts-db-submit-result`
* :program:`rhts-extend`
* :program:`rhts-system-info`
* :program:`rhts-test-checkin`
* :program:`rhts-test-update`

Environment variables
~~~~~~~~~~~~~~~~~~~~~

The harness sets a number of environment variables in the execution environment 
for tasks. The task can use these to adjust its behaviour as needed.

Task parameters (given in the Beaker job XML using ``<params/>``) are also 
passed to the task as environment variables.

Note that these environment variables *will not* be set when you log in to the 
system as a user over SSH or on the console.

.. envvar:: TEST

   The name of the current task. :envvar:`TASKNAME` is an alias for this 
   variable.

.. envvar:: TESTPATH

   Path to the directory containing this task.

.. envvar:: TESTRPMNAME

   NVRA (Name-Version-Release.Arch) of the current task RPM. Deprecated: do not 
   rely on tasks being packaged as RPMs.

.. envvar:: KILLTIME

   Expected run time of this task in seconds. This is declared in the TestTime 
   field in the task metadata (see :ref:`testinfo-testtime`), and is the length 
   of time by which the harness extends the watchdog at the start of the task.

.. envvar:: FAMILY
            DISTRO
            VARIANT
            ARCH

   Details of the Beaker distro tree which was installed for the current 
   recipe.

.. envvar:: SUBMITTER

   Email address of the Beaker user who submitted the current job.

.. envvar:: JOBID
            RECIPESETID
            RECIPEID
            TASKID

   Beaker database IDs for the current job, recipe set, recipe, and recipe-task 
   respectively. :envvar:`TESTID` and :envvar:`RECIPETESTID` are deprecated 
   aliases for :envvar:`TASKID`.

.. envvar:: TESTORDER

   Integer counter for tasks in the recipe. The value increases for every 
   subsequent task, and every peer task in the recipe set will have the same 
   value, but note that it *does not* increase by 1 for each task.

.. envvar:: REBOOTCOUNT

   Number of times this task has rebooted. The counter starts at zero when the 
   task is first run, and increments for every reboot. If a task triggers 
   a reboot, it can test this variable to decide which phase of the test to 
   enter so that it doesn't loop infinitely.

.. envvar:: RECIPETYPE

   The type of the recipe. Possible values are ``guest`` for a guest recipe, or 
   ``machine`` for a host recipe. See :doc:`virtualization-workflow`.

.. envvar:: GUESTS

   Deprecated. The recommended means of looking up details of guest recipes is 
   to fetch the recipe XML from the lab controller and parse it (see 
   :http:get:`/recipes/(recipe_id)/`).

.. envvar:: RECIPE_MEMBERS

   Space-separated list of FQDNs of all systems in the current recipe set.

.. envvar:: RECIPE_ROLE

   The role for the current recipe. See :doc:`multihost`.

.. envvar:: ROLE

   The role for the current task. See :doc:`multihost`.

.. envvar:: HYPERVISOR_HOSTNAME

   The hostname of a guest recipe's host. This is retrieved at recipe run time,
   and is not dynamically updated (i.e if you migrate your guest
   this variable will not be updated).

Additionally, one environment variable will be set for each recipe role defined 
in the recipe set. The name of the environment variable is the role name, and 
its value is a space-separated list of FQDNs of the systems performing that 
role. Similarly, each task role is set as an environment variable, but note 
however that task roles are only shared amongst recipes of the same type. That 
is, task roles for guest recipes are not visible to host recipes, and vice 
versa. See :doc:`multihost` for further details.

The following environment variables are set system-wide by Beaker at the start 
of the recipe.

.. envvar:: LAB_CONTROLLER

   FQDN of the lab controller which the current system is attached to.

.. envvar:: BEAKER

   FQDN of the Beaker server.

.. envvar:: BEAKER_JOB_WHITEBOARD

   Whiteboard of the current job.

.. envvar:: BEAKER_RECIPE_WHITEBOARD

   Recipe whiteboard for the current recipe.
