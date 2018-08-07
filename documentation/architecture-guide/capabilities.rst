Beaker's capabilities
=====================

Beaker is a full stack software and hardware integration testing system,
with the ability to manage a globally distributed network of test labs.

.. note::

   This page describes Beaker's capabilities as they currently exist. For
   more on how these capabilities are likely to evolve into the future, see
   the `technical roadmap <../../dev/tech-roadmap.html>`__. In particular,
   we already allow the use of alternative test harnesses (notably
   ``autotest``) that shouldn't need to rely on the RPM based task library
   and are planning to further reduce the reliance on Fedora specific
   technology (such as ``anaconda`` and ``yum``) by permitting dynamic
   provisioning through an associated OpenStack instance.

Beaker serves two primary purposes:

* It supports execution of complex multi-system test scenarios, collecting
  and publishing summary results and detailed logs
* It supports full stack integration testing of Fedora and derivatives
  (including Red Hat Enterprise Linux). This includes testing the installer,
  virtualization capabilities, a wide variety of hardware drivers, as well
  as ensuring other software components work correctly on a range of Fedora
  derived platforms.

It is the hardware inventory features needed to achieve the second aim that
distinguishes Beaker from most other task execution systems.


Beaker jobs
-----------

The core concept in Beaker is that of a :term:`job`. Jobs collect together a
number of "recipe sets" for reporting purposes, so that if any one
recipe set in the job fails, the overall job is also reported as a failure.

The :ref:`matrix-report-capability` allows users to get an overview of the
behaviour of the tasks within a job across multiple architectures.

Aside from the combined reporting, the recipe sets in a job have no
special relationship to each other - they are scheduled independently, may
run in an arbitrary order and may run in different hardware labs.

Jobs specifications are covered in some depth in the :ref:`job-xml` section
of the user guide.


Recipe sets
~~~~~~~~~~~

Each :term:`recipe set` in a job defines a collection of recipes that will
be executed as a group. This means that all recipes in a given recipe set
will be executed in the same hardware lab, that the recipes will only
be started once the last recipe in the set has been assigned a system,
and that those systems will only be released once all recipes in the
recipe set have completed.


Recipes
~~~~~~~

Each :term:`recipe` in a recipe set defines the characteristics of a
system to be used to run the recipe, as well as the operating system
distribution to be provisioned on that system. The recipe also defines
the tasks that are to be executed as part of the recipe. In addition
to running tasks directly on the system, recipes may also define guest
recipes, which will be created automatically as virtual machines on the
machine running the host recipe.

Recipes may also include various items to customise the kickstart file that
is used when provisioning the system.

.. note::

   As part of the dynamic virtualization feature described below, we are
   investigating the ability to use image based provisioning in OpenStack
   for recipes which do not have specific hardware requirements and aren't
   specifically aimed at testing the installer or otherwise require
   execution on a fresh installation to a bare metal system.


Test harnesses
~~~~~~~~~~~~~~

Actually executing tasks on a provisioned system requires a test harness.
Beaker uses the RPM-based ``beah`` as its default harness, but the use of
other harnesses can be requested in the recipe definition as defined in
the :ref:`alternative-harnesses`.


Tasks
~~~~~

For recipes using the default test harness (``beah``) each :term:`task` in
a recipe refers to a named task from the task library. These tasks
are RPMs that will be installed and executed on the target system.

Alternative test harnesses also make use of the task specification
format, but the exact interpretation will be up to the specific test
harness.


Guest recipes
~~~~~~~~~~~~~

To better support testing of hypervisor functionality, recipes may also
include guest recipe definitions. These are identical to full recipe
definitions, but rather than being provisioned directly by Beaker, they
are provisioned as local virtual machines by a task running on the host
system.

.. note::

   The tasks that are currently provided for controlling guest recipes
   are included in Beaker's git repository only as RPMs. This may
   change in the future.


Results
~~~~~~~

Beaker allows the recording of results against tasks as Pass, Fail and Warn.
A given task may have an unlimited number of results recorded against it,
with the worst result taken as the overall result of the task (so one or more
failures means the task fails, while one or more warnings means it is
a warning). If a task reports no results at all, that is interpreted as a
failure (as it may indicate the task never ran at all).

Task results are aggegated to recipe results, recipe results are aggregated
to recipe set results and recipe set results are aggregated to job results
in a similar fashion.


Result comments and waivers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker has an optional mechanism for reviewing job results.

Each recipe set in a job can be annotated with a response: either "ack" 
(acknowledgment), indicating that the results have been reviewed and are valid, 
or "nak" (negative acknowledgment), indicating that the results have been 
reviewed and are waived. A failure could be waived if it was caused by 
a problem in the external environment and is not related to the components 
being tested (for example, an outage of the lab network). The recipe set can 
also be annotated with a comment explaining the reason for the review.

Reviewing results is optional. If all results in the recipe set are Pass, its 
response is set to "ack" by default. Otherwise the recipe set is marked "needs 
review" until a reviewer updates the response to "ack" or "nak".

.. _watchdog-timer-capability:

Watchdog timers
~~~~~~~~~~~~~~~

Low level operating system testing is prone to rendering a machine
completely unresponsive, especially when testing experimental code.
Accordingly, Beaker supports two levels of watchdog timer, one running as
part of the test harness (called the "Local Watchdog") and one running
on the lab controller associated with the system running the recipe
(called the "External Watchdog").

If the local watchdog times out, it will abort the current task and attempt
to move on to the next one. If the external watchdog times out, it will
abort the entire recipe. Tasks are able to adjust the watchdogs dynamically
if they need more time, allowing the use of more aggressive default timeouts.


Log collection, monitoring, and archiving
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To help analyse failures, Beaker allows test harnesses to upload log files
(either in one piece or as multiple fragments). Logs can be uploaded at
the result, task and recipe levels.

In conjunction with an external console logging system (such as
`conserver <http://www.conserver.com/>`__), Beaker also supports the
automatic capture of the console logs for the duration of provisioning
and execution of a recipe. Console logs are also captured automatically
when running guest recipes (as Beaker configures the hypervisor to collect
the logs and pass them to the lab controller).

Beaker can optionally scan console logs to detect kernel panics and failed 
installations as soon as they happen (see :ref:`job-monitoring`).

Since preserving logs indefinitely may take up an undesirable amount
of space, Beaker also allows jobs to be tagged with a retention tag
that indicates when the logs should be deleted (with an association log
deletion script that should be run regularly, preferably in cron). See
:ref:`log-archiving-details` for more information.


Automatic SSH configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker allows users to register a public SSH key with the main server.
When systems are provisioned for a job, the job owner (and, for explicit
group jobs, their fellow group members) will be granted SSH access to the
provisioned systems.


Automatic system reservation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using a test harness that supports the task library, the
:ref:`reservesys task <reservesys-task>` may be used to request that the
system be automatically reserved after completion of the task (or only
if the task fails).

This allows the job owner to log in via SSH and investigate the failure,
which is essential when testing against hardware the user doesn't have
available locally.

.. note::

   A more reliable automatic reservation mechanism is planned, which will
   allow systems to be reserved even when aborted by the external watchdog,
   as well as when using a harness that doesn't support the task library.


.. _matrix-report-capability:

Job matrix report
~~~~~~~~~~~~~~~~~

The :ref:`job matrix report<matrix-report>` is used to provide an overview
of the behaviour of integration tests across multiple architectures. Using
either specific job identifiers or aggregating the results of multiple jobs
with a common whiteboard setting, the matrix report displays a summary of
the results of the tasks within the selected jobs, grouped by architecture.

The matrix report can be filtered to exclude any results that have been waived 
as part of the results review.


System provisioning
-------------------

Actually executing tasks requires that a system be provisioned, and the
appropriate operating system and test harness installed.

Beaker currently handles these operations through PXE booting (for the
initial operating system installation) and Anaconda kickstart files.


.. _lab-controller-capability:

Lab controllers
~~~~~~~~~~~~~~~

Every system in Beaker is associated with a specific lab controller.
Lab controllers run a TFTP server where they install the appropriate
PXE boot files to provision systems with the requested distribution.

The lab controller must be supported by a properly configured DHCP server,
which instructs systems to retrieving the PXE boot files from the lab
controller's TFTP server.

Lab controllers also provide the interfaces that allow tasks to report
results and upload logs, and provide interfaces to both tasks and
the main server to control the power state of systems (this external power
control is also used as the mechanism that attempts to restore a system
to a useful start after an external watchdog timeouts).

Multiple lab controllers may be located at a single site (e.g. for
network isolation), or they may be geographically separated. Note that
having multiple small labs rather than one large one will limit the size
of the multi-host jobs which can be effectively scheduled.


Distros
~~~~~~~

Beaker is primarily built to handle integration testing of a full
operating system. This is most clearly indicated by the current approach to
system provisioning: Beaker always provisions machines from bare metal,
and provides a rich query mechanism to choose the specific distro tree
to install.

As Beaker assumes lab controllers may be geographically distributed,
distros must be :ref:`imported separately<importing-distros>` from a local
mirror for each lab controller. Recipe sets that include recipes with
specific distribution requirements will only consider systems in labs
with those distributions available.

Beaker allows distros to be tagged with arbitary labels. In combination
with the :ref:`distro update script<stable-distro-tagging>` that tags new
distros as stable only if they're installed successfully on all supported
architectures, this means higher level tests can be written to ensure they
have at least been checked to ensure they can be installed successfully.


Power scripts
~~~~~~~~~~~~~

To handle power cycling and rebooting systems, Beaker requires remote
power control. This is handled through the use of "power scripts", which
must be installed locally on the lab controller. Several power scripts
are shipped as part of the Beaker software, including scripts for
controlling power through the ``ipmitool`` command line client and
externally created virtual machines through ``virsh``.


Hardware inventory scan
~~~~~~~~~~~~~~~~~~~~~~~

The :ref:`inventory task<inventory-task>` can be run on systems in Beaker
to upload a detailed analysis of the system components to Beaker. This
information can then be used when submitting recipes to request that they
be run on specific architectures, systems with specific hardware installed,
virtual machines running on particular hypervisors, etc.


System loans, manual and forced provisioning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Large Beaker installations are likely to include esoteric hardware that may
not be available elsewhere within an organisation.

Beaker provides a "loan" mechanism, where systems may be temporarily
made available to specific users for their exclusive use, regardless of
whether or not the user would normally have access to that system.

Systems may be placed in "manual" mode, which means users can provision a
distro directly without worrying about interference from the automated
scheduler.

Capability for "forced provisioning" a system is also available via
the ``force`` attribute of the ``<hostRequires/>`` element (See
:ref:`forced system provisioning<forced-system>`). An example of why
this capability is useful is that it allows running
diagnostic jobs on systems marked as ``broken`` before they are
considered ready for use again.


Dynamic virtualization
~~~~~~~~~~~~~~~~~~~~~~

Dynamic virtualization is an experimental feature of Beaker, that aims to
avoid the limitations of always provisioning systems from bare metal
using kickstart files, without reinventing capabilities already provided
by existing open source Infrastructure-as-a-Service components.

There is an initial limited capabability (based on oVirt engine) that still
relies on kickstart files for installation and configuration, but it is
expected that this will be replaced with a more efficient mechanism based
on OpenStack (including the post-install code execution tools provided by
Nova, the OpenStack Compute component).


Other supporting capabilities
-----------------------------

User and group management
~~~~~~~~~~~~~~~~~~~~~~~~~

Effectively sharing access to thousands of systems by hundreds of users
requesting execution of millions of task is not a simple problem.

Beaker's user and group management features are designed to help assist with
this. The group model allows ad hoc creation of groups by users, or else
admins can create predefined groups based on an external LDAP service.

Once groups are defined, they can be used to share job access, as well as
to share rights to use and manage systems and groups.

The "submission delegation" feature also allows users to grant other users
the ability to submit jobs on their behalf, which is useful for test
automation purposes.


Web services
~~~~~~~~~~~~

The main Beaker server currently exposes functionality to clients over both
XML-RPC and HTTP. This interface is documented :ref:`here<server-api>`.

While the native ``beah`` test harness uses XML-RPC to communicate with
the lab controller, the public lab controller API for use by alternative
harnesses is based on HTTP. It is documented
:ref:`here<alternative-harnesses>`.


Incidental functionality
------------------------

There are certain ways of using Beaker, that, while necessarily possible
due to the way Beaker works, aren't recommended. Feature requests related
solely to these ways of (ab)using Beaker that don't benefit the primary
task execution use cases for the project are almost certain to be rejected.


Infrastructure-as-a-Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The mechanisms that Beaker provides to aid in fault investigation and
effective sharing of unusual hardware configurations can also be used with
commodity hardware to provide a basic "Infrastructure-as-a-Service"
capability.

However, while using Beaker this way may be an improvement over managing
systems manually, Beaker does not aim to compete with actual
Infrastructure-as-a-Service related projects like oVirt Engine and OpenStack.


Legacy functionality
--------------------

Current versions of Beaker also offer some legacy functionality that may be
in use as part of existing Beaker installations, and thus is not subject to
immediate deprecation.


Asset management
~~~~~~~~~~~~~~~~

Beaker includes some rudimentary capabilities for asset management of
systems (physical location data, purchase prices, etc). This functionality
is now considered to be outside Beaker's scope. It is retained solely for
the benefit of existing installations that have not yet migrated to a full
data centre inventory management solution
(such as `OpenDCIM <http://www.opendcim.org/>`__).
