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
installed and other files. If there is a problem in the installation,
the data in these files can often be used to determine the cause.

.. _reservesys-task:

/distribution/reservesys
========================

The ``/distribution/reservesys`` task reserves a system for a specific
time frame to aid post-test analysis. You would usually append this
task in your recipe so that the system is available for you to login
after the other tasks have been run, but before the system is
returned to Beaker. :ref:`system-reserve` describes system reservation
in detail.

.. _inventory-task:

/distribution/inventory
=======================

The ``/distribution/inventory`` task is useful for the administrator of
a Beaker installation to gather detailed hardware data about
Beaker's test systems. Hardware devices which are probed include disk
drives, graphics hardware and network devices. When this task is run
on a test system, it retrieves this information and sends it to the Beaker
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

This task is used by the Beaker developers to run the test suite
every time a new patch is pushed to the development branch to help
prevent any regressions in the code base.

.. _dummy-task:

/distribution/utils/dummy
=========================

This is a placeholder task used to align task execution across different
recipes in a multi-host recipe set. See :ref:`multihost-tasks` for details.


.. _virt-install-task:

/distribution/virt/install
==========================

The ``/distribution/virt/install`` task is responsible for installing
a virtual machine (defined as a 'guest recipe' in Beaker). It does this via
``virt-install``. The task is defined in the host recipe, often along with
``/distribution/virt/start``. For example::

  <task name="/distribution/install" role="SERVERS">
    <params/>
  </task>
  <task name="/distribution/virt/install" role="SERVERS">
    <params/>
  </task>
  <task name="/distribution/virt/start" role="SERVERS">
    <params/>
  </task>

Be aware that ``/distribution/virt/start`` and ``/distribution/virt/install``
should never be defined in the guest recipe itself.


.. _virt-start-task:

/distribution/virt/start
========================

The ``/distribution/virt/start`` task is used for starting a virtual machine,
via ``virsh start``. Please see :ref:`virt-install-task` for examples on how to
use it with ``/distribution/virt/install``.

Other tasks
===========

There are a number of other tasks that you will find in the
:file:`Tasks/` sub-directory of the Beaker `source tree`_. Most of
these tasks (besides the ones we discussed above), have a
:file:`PURPOSE` file which contains a brief description of what
the task does.

.. _source tree: http://git.beaker-project.org/cgit/beaker/
