Integration with Graphite
=========================

Beaker can optionally be configured to send metrics to the
`Graphite <http://graphite.wikidot.com/>`_ real-time graphing system.
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

Beaker sends three types of metrics: counters, gauges, and durations. (A
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

Useful graphs
-------------

Below are some links to useful graphs showing the overall health and
performance of your Beaker system. These URLs could be used as the basis
for a dashboard or given to users. The URLs assume the default metric
name prefix ``beaker.`` with a Graphite instance at
``graphite.example.com``.

Utilisation of all systems
    ::

        http://graphite.example.com/render/?width=1024&height=400
            &areaMode=stacked
            &target=beaker.gauges.systems_idle_automated.all
            &target=beaker.gauges.systems_idle_broken.all
            &target=beaker.gauges.systems_idle_manual.all
            &target=beaker.gauges.systems_manual.all
            &target=beaker.gauges.systems_recipe.all

Utilisation of shared systems
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


