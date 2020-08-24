Upgrading an existing installation
==================================

Before you start, check the :doc:`release notes <../whats-new/index>` for any
specific instructions beyond the general steps described here. If you are
upgrading through multiple releases (for example, from 0.10 to 0.13) follow the
instructions for all of the releases.

Always upgrade the Beaker server before the lab controllers, in case the new
lab controller version relies on interfaces in the new server version.

Maintenance releases
--------------------

You can upgrade to a new maintenance release within the same *x.y* series with
no interruption to Beaker.

Use Yum to upgrade the relevant packages. The packages will automatically
restart any running Beaker daemons, but you should signal the Apache server to
reload its configuration.

On the Beaker server::

    yum upgrade beaker-server
    service httpd graceful

Then, on the lab controllers::

    yum upgrade beaker-lab-controller
    service httpd graceful

Feature releases
----------------

When upgrading to a new feature release of Beaker, some database changes may be
required. These will be detailed in the release notes.

Database schema changes can interfere with Beaker's normal operation, so you
should stop all Beaker services before beginning the upgrade. The sequence of
events in this case is:

1. Stop Beaker daemons on the lab controllers.
2. Stop Apache and beakerd on the Beaker server.
3. Use Yum to upgrade all relevant packages.
4. Run :program:`beaker-init` to apply database changes.
5. Start Apache and beakerd on the Beaker server.
6. Extend all watchdogs using :program:`bkr watchdogs-extend`.
7. Start Beaker daemons on the lab controllers.

Note that during the outage period, running jobs will be affected. The harness
will be unable to report in to Beaker, so the effects may include missing
results and missing logs. Extending all watchdogs at the end of the upgrade
will mitigate the problem, by allowing recipes to complete normally if their
watchdog time was exceeded during the outage.

.. _updating-harness-packages:

New harness packages
--------------------

New releases of Beaker occasionally include updated versions of ``beah``,
``rhts``, and other packages which are installed on test systems. The latest
versions are `published on the Beaker web site
<http://beaker-project.org/yum/harness/>`__.

To update your Beaker server's copy of the harness packages, run the
:program:`beaker-repo-update` command. See :doc:`beaker-repo-update
<man/beaker-repo-update>` for more details.

.. _downgrading:

Downgrading
-----------

The procedure for downgrading to an earlier version of Beaker is similar to the
upgrade procedures described above, with the following differences:

* Use ``yum downgrade`` instead of ``yum upgrade``, naming the specific package
  version you are downgrading to.

* If you are downgrading to an earlier release series, run
  ``beaker-init --downgrade=<version>`` to downgrade the database schema
  *before* downgrading any packages. The table below lists the database version
  corresponding to each Beaker release series.

.. This table is also encoded in beaker-init, don't forget to update it there!

==============  ================
Beaker release  Database version
==============  ================
28              ``4b3a6065eba2``
27              ``4cddc14ab090``
26              ``348daa35773c``
25              ``1ce53a2af0ed``
24              ``f18df089261``
23              ``2e171e6198e6``
22              ``54395adc8646``
21              ``171c07fb4970``
20              ``19d89d5fbde6``
19              ``53942581687f``
0.18            ``431e4e2ccbba``
0.17            ``431e4e2ccbba``
0.16            ``2f38ab976d17``
0.15            ``49a4a1e3779a``
0.14            ``057b088bfb32``
0.13            ``41aa3372239e``
0.12            ``442672570b8f``
==============  ================
