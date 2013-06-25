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
restart any running Beaker daemons, but you should explicitly reload the Apache 
server.

On the Beaker server::

    yum upgrade beaker-server
    service httpd reload

Then, on the lab controllers::

    yum upgrade beaker-lab-controller
    service httpd reload

Feature releases
----------------

When upgrading to a new *x.y* release of Beaker, some database changes may be 
required. These will be detailed in the release notes.

Database schema changes can interfere with Beaker's normal operation, so you 
should stop all Beaker services and the Apache server before beginning the 
upgrade. Then use Yum to upgrade the relevant packages, perform the database 
changes, and start all Beaker services.

New harness packages
--------------------

New releases of Beaker occasionally include updated versions of ``beah``, 
``rhts``, and other packages which are installed on test systems. The latest 
versions are `published on the Beaker web site 
<http://beaker-project.org/yum/harness/>`__.

To update your Beaker server's copy of the harness packages, run the 
``beaker-repo-update`` command. You can pass the ``-b`` option to update from 
an alternative URL. For example, to update your Beaker server with the latest 
release candidate harness packages::

    beaker-repo-update -b http://beaker-project.org/yum/harness-testing/

Downgrading
-----------

The procedure for downgrading to an earlier version of Beaker is similar to 
upgrading: use ``yum downgrade`` instead of ``yum upgrade``, and follow the 
rollback instructions in the release notes if applicable.
