.. _graphite:

Integration with Graphite
=========================

Beaker can optionally be configured to send metrics to the
`Graphite <http://graphite.wikidot.com/>`__ real-time graphing system.
Beaker sends metrics via UDP for efficiency, and to avoid impacting the
performance and reliability of the system, so a version of Graphite with
UDP listener support is required.

To enable Graphite integration, configure the hostname and port of the
carbon daemon in ``/etc/beaker/server.cfg``:

::

    carbon.address = ('graphite.example.invalid', 2023)
    carbon.prefix = 'beaker.'

The ``carbon.prefix`` setting is a prefix applied to the name of all
metrics Beaker sends to Graphite. You can adjust the prefix to fit in
with your site’s convention for Graphite metric names, or to distinguish
multiple Beaker environments sharing a single Graphite instance.

Aggregating metrics
-------------------

Beaker does not perform aggregation of metrics, and expects to send
metrics to Graphite's carbon-aggregator daemon (which forwards the
metrics to carbon-cache for storage after aggregating them). The
``carbon.address`` setting should therefore be the address of the
carbon-aggregator daemon.

Beaker may send three types of metrics: counters, gauges, and durations. (A
duration is equivalent to a gauge except that it is in seconds instead
of arbitrary units.) The type appears at the start of the metric name,
after the configured prefix. For example, assuming the default prefix
``beaker.``, Beaker will periodically report the number of running
recipes as ``beaker.gauges.recipes_running``.

You should configure suitable aggregation rules for Beaker in
``/etc/carbon/aggregation-rules.conf``. The following example assumes
the default prefix ``beaker.`` and 1-minute storage resolution:

::

    beaker.durations.<name> (60) = avg beaker.durations.<name>
    beaker.counters.<name> (60) = sum beaker.counters.<name>
    beaker.gauges.<name> (60) = avg beaker.gauges.<name>

System utilization metrics
--------------------------

To provide a real-time view of system utilization, Beaker updates the
following gauges::

    beaker.gauges.systems_idle_automated
    beaker.gauges.systems_idle_broken
    beaker.gauges.systems_idle_manual
    beaker.gauges.systems_manual
    beaker.gauges.systems_recipe

These metrics describe the current utilization of Automated, Manual
and Broken systems in Beaker.

Automated systems are under the control of the Beaker scheduler, and are
available to run submitted jobs. They are covered by the ``recipe``
(currently waiting for other recipes in a recipe set, provisioning the
system or running a task as part of a recipe) and ``idle_automated``
(waiting to be assigned to a recipe) gauges.

Manual systems are available to Beaker users, but not to the scheduler. They
are covered by the ``manual`` (assigned to a specific user) and
``idle_manual`` (not assigned to anyone) gauges.

Broken systems, covered by the ``idle_broken`` gauge, are awaiting
investigation by system administrators before being placed back in the pool
of available systems.

In addition to the metrics for every system known to Beaker, live metrics
are also available for systems in the shared pool, which are equally
available to all users of a Beaker installation. To access these metrics,
replace ``.all`` with ``.shared``.

Each of the system utilization gauges is also available broken down by
architecture and by the lab controller that manages that system. For
example, information on the idle x86_64 machines can be accessed as::

    beaker.gauges.systems_idle_automated.by_arch.x86_64

As a system may support multiple architectures (e.g. both "i386" and
"x86_64", the ``by_arch`` metrics may not add up to the ``all`` metrics).

Information on the machines managed by a particular lab controller can be
accessed as::

    beaker.gauges.systems_idle_automated.by_lab.lchost_example_com


Recipe queue metrics
--------------------

To provide a real-time view of the recipe queue, Beaker updates the
following gauges::

    beaker.gauges.recipes_new.all
    beaker.gauges.recipes_processed.all
    beaker.gauges.recipes_queued.all
    beaker.gauges.recipes_scheduled.all
    beaker.gauges.recipes_running.all
    beaker.gauges.recipes_waiting.all

The ``new`` and ``processed`` states are transient states used when a job is
initially submitted to Beaker. All recipes should move relatively quickly
through these states to the ``queued`` state. If this isn't happening, it
is a sign that new jobs are arriving faster than the scheduler is able to
process them.

The ``queued`` state indicates that initial processing of the recipe is
complete, and it is ready to be assigned to a system. Depending on the
strictness of the recipe's host requirements, and the availability of
suitable systems, recipes may spend an extended period of time in this
state.

The ``scheduled`` state indicates that the recipe has been assigned a
system (or a virtualized resource), but is waiting for other recipes in
the same recipe set to be assigned a resource.

The ``waiting`` state indicates that the recipe is waiting for the initial
reboot of the system that starts the kickstart-based provisioning process.
Recipes should move relatively quickly through this state to the ``running``
state. If this isn't happening, it is a sign that there is a problem
somewhere in the Beaker installation (e.g. if the ``beaker-provision``
service is not running on one of the lab controllers, recipes assigned to
that lab will get stuck in this state).

The ``running`` state indicates that the recipe is either waiting for the
provisioning to complete, or is actually executing tasks on
the assigned resource.

The number of recipes in ``scheduled`` and ``running`` may exceed the number
of systems assigned to a recipe (as indicated by the ``systems_recipe``
gauge) as recipes may be executing on a dynamically created virtual machine.

To observe the utilization of dynamic virtualization resources, replace
``.all`` with ``.dynamic_virt_possible``. These metrics show recipes which
are either still under consideration for creation of a dynamic virtual
machine, or which have already been assigned one.

Each of the recipe queue gauges is also available broken down by
the architecture of the distro tree associated with the recipe. For
example, information on the recipes currently in Beaker that require
x86_64 machines can be accessed as::

    beaker.gauges.recipes_queued.by_arch.x86_64


Dirty job count
---------------

Beaker populates this gauge with the number of jobs currently marked "dirty" in 
the database::

    beaker.gauges.dirty_jobs

Jobs become "dirty" when their scheduling state has been changed (for example, 
the user cancels the job, or the harness completes a task) but the scheduler 
has not yet handled the status update.

A large value for this gauge indicates that there may be a problem with the 
scheduler causing a backlog of unhandled status updates.


System command metrics
----------------------

Similar to the recipe queue metrics described above, Beaker provides 
a real-time view of the system command queue with the following gauges::

    beaker.gauges.system_commands_queued.all
    beaker.gauges.system_commands_running.all

The ``queued`` state represents commands which are in the queue but the 
:program:`beaker-provision` daemon has not started running them yet. The 
``running`` state represents commands which have started but not finished yet.

A large value for the ``queued`` gauge indicates that there may be a problem 
with the :program:`beaker-provision` daemon on a lab controller causing 
a backlog of queued commands.

In addition, Beaker updates the following counters when a system command has 
finished (whether successfully or not)::

    beaker.counters.system_commands_completed.all
    beaker.counters.system_commands_aborted.all
    beaker.counters.system_commands_failed.all

Each of the command queue gauges and counters is also available broken down by 
the lab controller responsible for running the command.


Useful graphs
-------------

Below are some links to useful graphs showing the overall health and
performance of your Beaker system. These URLs could be used as the basis
for a dashboard or given to users. The URLs assume the default metric
name prefix ``beaker.`` with a Graphite instance at
``graphite.example.com``.

Utilization of all systems
    ::

        http://graphite.example.com/render/?width=1024&height=400
            &areaMode=stacked
            &target=beaker.gauges.systems_idle_automated.all
            &target=beaker.gauges.systems_idle_broken.all
            &target=beaker.gauges.systems_idle_manual.all
            &target=beaker.gauges.systems_manual.all
            &target=beaker.gauges.systems_recipe.all

Utilization of shared systems
    ::

        http://graphite.example.com/render/?width=1024&height=400
            &areaMode=stacked
            &target=beaker.gauges.systems_idle_automated.shared
            &target=beaker.gauges.systems_idle_broken.shared
            &target=beaker.gauges.systems_idle_manual.shared
            &target=beaker.gauges.systems_manual.shared
            &target=beaker.gauges.systems_recipe.shared

Recipe queue
    ::

        http://graphite.example.com/render/?width=1024&height=400
            &areaMode=stacked
            &target=beaker.gauges.recipes_new.all
            &target=beaker.gauges.recipes_processed.all
            &target=beaker.gauges.recipes_queued.all
            &target=beaker.gauges.recipes_running.all
            &target=beaker.gauges.recipes_scheduled.all
            &target=beaker.gauges.recipes_waiting.all

Recipe throughput
    ::

        http://graphite.example.com/render/?width=1024&height=400
            &target=beaker.counters.recipes_completed
            &target=beaker.counters.recipes_cancelled
            &target=beaker.counters.recipes_aborted


