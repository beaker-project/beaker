Tasks provided with Beaker
--------------------------

Besides the custom tasks which Beaker users would write for a specific
testing scenario, there are a number of tasks which are distributed
and maintained along with Beaker. Among these,
``/distribution/install`` and ``/distribution/reservesys`` are
essential for Beaker's operation. ``/distribution/inventory`` is not
essential for Beaker's operation, but it is required for accurate
functioning of Beaker's ability to schedule jobs on test systems
meeting user specified hardware criteria. The task,
``/distribution/beaker/dogfood`` runs Beaker's test suite (hence, the
name `dogfood`) and is perhaps only useful for meeting certain
specific requirements of the Beaker developers.


/distribution/install
=====================

The purpose of this task is to report back on the system install
(provisioning). It is usually added before any scenario specific tasks
so that it is run immediately after the system has been provisioned.

This task uploads the kickstart used by the Anaconda installation
program to provision the system, the boot loader configuration file,
error logs, a file containing the list of packages which were
installed and other files. Hence, if there was a problem in the
installation, the data in these files can be referred to find
the reason for the same.

/distribution/reservesys
========================

The ``/distribution/reservesys`` task reserves a system for a specific
time frame to aid post-test analysis. You would usually append this
task in your recipe so that the system is available for you to login
after the other tasks have been run (otherwise, the system is returned
to Beaker).

The task's behavior can be configured using a number of parameters
(similar to any other Beaker task):

- :envvar:`RESERVE_IF_FAIL`: If this parameter is defined then the
  result of the recipe is checked. The system is reserved, *only* if the
  recipe did not pass. If it passed, this "test" is reported back to
  Beaker as a pass and the next task in the recipe (if any) begins
  execution. The parameter should be defined as: ``<param
  name="RESERVE_IF_FAIL" value= "True" />``. (In fact, it can be
  defined to have *any* non-empty string as value. For example,
  ``<param name="RESERVE_IF_FAIL" value= "False" />`` will have the
  same effect). If you want to reserve the system irrespective of the
  result of the test, do not specify this variable at all.

- :envvar:`RESERVETIME`: Using this parameter, you can define the duration
  (in seconds) for which you want to reserve the system upto a maximum
  of 356400 seconds (99 hours). If this variable is not defined, the
  default reservation is for 86400 seconds (24 hours) (Also, see
  :ref:`return-early-extend-time` below).

For example, to define both these parameters when you specify the task
in your job description, you would use the following::

    <task name="/distribution/reservesys" role="STANDALONE">
      <params>
        <param name="RESERVE_IF_FAIL" value="True" />
        <param name="RESERVETIME" value="172800" />
      </params>
    </task>

Notification
~~~~~~~~~~~~

Depending on whether you set the :envvar:`RESERVE_IF_FAIL` parameter appropriately
and its implications (as described), once the system has been
reserved, you will receive an email with the subject "[Beaker Machine
Reserved] test-system.example.com" and other information. This is a
notification that the system has now been reserved and you can connect
to it (using an SSH client, either using the username and password or
your public key).

The notification email is sent from the test system. This implies that
in case of a problem in network connectivity between your email server
and the test system, the notification email will not be received.


.. _return-early-extend-time:

Returning early and extending reservation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The email also includes information about returning the system
early or extending your reservation time. To return the system early,
execute :program:`return2beaker.sh` from your terminal (after you have
logged in to the system).

To extend the reservation time, execute :program:`extendtesttime.sh`
which will ask prompt the duration for which you want to extend the
reservation starting from the present time.


/distribution/inventory
=======================

The ``/distribution/inventory`` task is useful for the administrator of
a Beaker installation to gather detailed hardware data about
Beaker's test systems. Hardware devices which are probed include disk
drives, graphics hardware and network devices. When this task is run
on a test system, it retrieves these data and sends it to the Beaker
server where it is updated in the main database.

This data can then be used by Beaker to schedule a job for which a
specific hardware requirement may have been specified (See:
:ref:`device specification in jobs <device-specs>`). Hence, it is a
good idea to run this task on every system to ensure that the hardware
details are correctly updated in Beaker's database.


/distribution/beaker/dogfood
============================

The ``/distribution/beaker/dogfood`` task runs Beaker's test suite (unit
tests and selenium tests) on a test system. It can be configured to
either run the tests from the development branch of Beaker or the most
recent released version.

This task is being used by the Beaker developers to run the test suite
every time a new patch is pushed to the development branch to help
prevent any regressions in the code base.

Other tasks
===========

There are a number of other tasks that you will find in the
:file:`Tasks/` sub-directory of the Beaker `source tree`_. Most of
these tasks (besides the ones we discussed above), would have a
:file:`PURPOSE` file which contains a brief description of the what
the task does.

.. _source tree: http://git.beaker-project.org/cgit/beaker/
