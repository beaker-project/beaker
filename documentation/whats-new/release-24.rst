What's New in Beaker 24?
========================

Beaker 24 brings improved OpenStack integration, conditional reservations, and many
other improvements.

Improved OpenStack integration
------------------------------

In this release the integration with OpenStack for dynamically creating VMs has
been improved. It is aimed to allow people to use OpenStack in production Beaker
instances.

Beaker no longer supports the Nova Networking API for creating virtual networks.
It now relies on the Neutron API instead, in line with modern OpenStack deployment
practices.

Previously Beaker needed to store the user's OpenStack credentials directly which
is insecure. In this release, Beaker now uses Keystone trusts for authentication
which can be created in your user preferences (see :doc:`../user-guide/user-preferences`)
or by using the :program:`bkr update-openstack-trust` command.

Beaker now supports dispatching multiple requests to OpenStack in parallel which
eliminates chances of causing a scheduling bottleneck.

When an OpenStack instance is launched, it is assigned with a floating ip address
and can be reached over SSH.

Refer to :ref:`openstack` for information about how to configure this feature 
in your Beaker instance.

Here is a list of issues resolved and enhancements made for OpenStack integration:

* :issue:`1299413`: support OpenStack Neutron networking
* :issue:`1100519`: don't store the user's OpenStack credentials in Beaker
* :issue:`1396913`: CLI to create Keystone trusts
* :issue:`1127574`: dispatch multiple requests to OpenStack in parallel
* :issue:`1396851`: assign a floating IP address to each instance
* :issue:`1399445`: port beaker-create-ipxe-image to the OpenStack Images API v2
* :issue:`1360117`: migrate the keystone API from v2.0 to v3
* :issue:`1361936`: no watchdog for recipe provisioned by OpenStack after reboot
* :issue:`1389562`: The :program:`beaker-create-ipxe-image` now saves the image
  on disk when passing :option:`beaker-create-ipxe-image --no-upload`
* :issue:`1361961`: Show the progress of creating an OpenStack instance with the kernal
  options in the recipe page
* :issue:`1364288`: Display the openstack instance link on the recipe page
* :issue:`1397649`: Beaker now always picks the OpenStackflavor with least RAM
  when running recipes on OpenStack
* :issue:`1396874`: Openstack instance link is removed when the job is not
  finished or deleted
* :issue:`1413783`: RHEL4 recipes are excluded from OpenStack because RHEL4
  does not obey DHCP option 26 for controlling MTU

(Contributed by Matt Jia, Róman Joost, Hui Wang, and Dan Callaghan.)

New result type Skip
--------------------

Beaker now supports a new result type, Skip. A task can report this result to 
Beaker in the same way that it reports Pass, Fail, or Warn using the standard 
:program:`rhts-report-result` command or its wrappers. You can use this result 
type to indicate that a task is not applicable on a particular platform, for 
example.

Version 4.72 of the ``rhts`` test development and execution library and version 0.7.11
of the Beah test harness are released in order to support the new Skip result.

Conditional reservations
------------------------

You can now conditionally reserve the system at the end of your recipe when 
using the ``<reservesys/>`` element. Refer to :ref:`system-reserve`
for more information.

(Contributed by Dan Callaghan in :issue:`1100593`.)

Job results XML enhancements
----------------------------

The job results XML format now includes the following additional timestamp 
attributes:

* ``start_time`` and ``finish_time`` on the ``<recipe/>`` element
* ``start_time`` and ``finish_time`` on the ``<task/>`` element
* ``start_time`` on the ``<result/>`` element

Timestamps are in the form ``YYYY-mm-dd HH:MM:SS`` and expressed in UTC.

The job results XML format now includes the filename and URL for each log file 
which was uploaded by the job. Each log is represented by a ``<log/>`` element 
and is contained in a ``<logs/>`` element, which appears inside the 
``<recipe/>``, ``<task/>``, and ``<result/>`` elements.

In case the job results XML with logs is too large, you can request the 
original format without logs by passing the :option:`--no-logs
<bkr job-results --no-logs>` option to the :program:`bkr job-results` command.

(Contributed by Dan Callaghan in :issue:`1037594` and :issue:`915319`.)

User interface improvements
---------------------------

The web UI for task library has been revamped in order to improve performance,
simplify interactions, and improve code maintainability. The improved task library grid
also offers more powerful search functionality. (Contributed by Tyrone Abdy in :issue:`1346620`,
:issue:`1081271`, and :issue:`887068`.)

On the recipe page, the hostname link is replaced with a drop down menu. This
will allow users to easily copy the hostname of the system, access to the
system info, report system problem, and link to the web application running on the
system. (Contributed by Dan Callaghan and Jon Orris in :issue:`1366191`, :issue:`1362595`,
and :issue:`1323154`.)

Each task in a recipe is now represented by an individual segment in the 
progress bar, color-coded to indicate its result and with a link to the task's 
results. Previously the progress bar only showed an aggregate proportion for 
each result type in the recipe. (Contributed by Dan Callaghan in :issue:`1352760`.)

Beaker client improvements
--------------------------

Three new beaker commands, :program:`bkr pool-systems`, :program:`bkr group-list`,
and :program:`bkr pool-list` are now available for listing the systems in a pool,
groups owned by the given user and system pools owned by the given user or group.
(Contributed by Hui Wang in :issue:`1374620`, :issue:`1373409`, and :issue:`1373400`.)

Two new options :option:`--finished <bkr job-list --finished>` and :option:`--unfinished <bkr job-list --unfinished>`
are available for :program:`bkr job-list` to filter out running and completed
jobs.
(Contributed by Dong Wang in :issue:`1175853`.)

The :program:`bkr` client now always loads system-wide configuration from  
:file:`/etc/beaker/client.conf` and per-user configuration from 
:file:`~/.beaker_client/config`. Settings in the per-user configuration file 
override the system-wide configuration. Previously, if the per-user 
configuration file existed, the system-wide configuration would not be loaded.
(Contributed by qhsong and Dan Callaghan in :issue:`844364`.)

If the :program:`bkr` client is making a request to the server and it fails, 
the client will print an additional warning message if the server's major 
version is less than the client's. This is to help detect the case where the 
client is attempting to use a new API against an older server which does not 
support it. (Contributed by Dan Callaghan in :issue:`1029287`.)

The :program:`bkr list-labcontrollers` and :program:`bkr list-systems` is
renamed to :program:`bkr labcontrollers-list` and :program:`bkr systems-list`
respectively which is consistent with other similar commands. The previous command
names have been kept as deprecated aliases for backwards compatibility.
(Contributed by Hui Wang in :issue:`1379971` and :issue:`1379967`.)

The ``beaker-client`` package is published on PyPI and can be installed using pip.
(Contributed by Dan Callaghan in :issue:`1278605`.)

The :program:`bkr whoami` command now checks SSL certificate validity and uses
the CA certificate specified in :file:`client.conf`.
(Contributed by Dan Callaghan in:issue:`1142566`.)

Other new features and enhancements
-----------------------------------

The :program:`product-update` server utility now accepts a new option 
:option:`--product-url <product-update --product-url>` for loading product data
from the given URL. It now also supports loading JSON formatted data in addition
to XML. (Contributed by Dan Callaghan in :issue:`1403084`.)

Users can now opt out of Beaker email notifications in their user preferences. (Contributed by
Blake McIvor in :issue:`1136748`.)

A new kickstart metadata variable ``pkgoptions`` is defined to specify %packages options.
If it is set, the default option ``--ignoremissing`` will be overridden. (Contributed
by Jeffrey Bastian and Dan Callaghan in :issue:`1387256`.)

Beaker now records and displays the start time and finish time for each power 
command as it is executed.
(Contributed by Dan Callaghan in :issue:`1318524`.)

Prototype systems now can be selected in the Reserve Workflow if you have the
necessary permissions. (Contributed by Dan Callaghan in :issue:`1099142`.)

The HTTP APIs for getting the activity logs now support id filtering.
(Contributed by Matt Jia in :issue:`1401964`.)

Notable changes
---------------

The External Reports feature has been removed. Administrators who want to link 
to external reports (or any other resources hosted outside Beaker) should use 
the theming support to inject extra HTML into Beaker's web UI. Refer to 
:ref:`theming-custom-markup` for an example of injecting a site-specific link 
in the Help menu. (Contributed by Dan Callaghan in :issue:`1389627`.)

Beaker now uses the :program:`createrepo_c` tool by default when generating Yum 
repositories, since it is faster and more memory-efficient. It is still 
possible for Beaker administrators to switch back to the original 
:program:`createrepo` implementation by setting ``beaker.createrepo_command`` 
in the server configuration file. (Contributed by Dan Callaghan in :issue:`1347156`.)

The ``force=""`` attribute for the ``<hostRequires/>`` element will now bypass 
any excluded family restrictions for the named system. Previously, if you 
submitted a recipe requesting a distro which was excluded on the named system, 
the recipe would be aborted with a message that it "does not match any 
systems". (Contributed by Dan Callaghan in :issue:`1384527`.)


Bug fixes
---------

A number of bug fixes are also included in this release:

* :issue:`1263921`: Beaker now disallows creating groups with a forward-slash (``/``)
  character in the name.
  (Contributed by Blake McIvor)

* :issue:`1366175`: The :program:`bkr system-details` command now uses the CA certificate
  specified in client.conf.
  (Contributed by Dan Callaghan)

* :issue:`1336329`: The :program:`bkr job-clone` command now properly reports an error
  message when not given any argument.
  (Contributed by Blake McIvor)

* :issue:`1358557`: The task icons now are updated to reflect whether the tasks
  are expanded when using the recipe task anchors.
  (Contributed by Matt Jia)

* :issue:`1401749`: The :guilabel:`Take` operation is no longer offered for broken systems.
  (Contributed by Róman Joost)

* :issue:`1399867`: When extending your reservation on the recipe page, you can now specify
  the duration in minutes or hours. Previously only seconds were accepted.
  (Contributed by Róman Joost)

* :issue:`980711`: The priority box is always shown on the job page regardless of
  the state.
  (Contributed by Blake McIvor)

* :issue:`1358063`: The power password is censored in the logs generated by
  :program:`beaker-provision` without leaking it.
  (Contributed by Dan Callaghan)

* :issue:`1391321`: Fixed non-stable URLs of the job log files in JUnit XML results.
  (Contributed by Matt Jia)

* :issue:`1391282`: Fixed non-stable URLs in the output generated by the :program:`bkr job-logs`.
  (Contributed by Matt Jia)

* :issue:`1366100`: XMLRPC retries in lab controller daemons are now logged again.
  (Contributed by Dan Callaghan)

* :issue:`1362370`: The recipe page installation progress now only shows "Netboot configured"
  when the command has been successfully completed and netboot configuration is in place.
  Previously the "Netboot configured" item would appear when the command was enqueued,
  even if it was not successfully completed.
  (Contributed by Dan Callaghan)

* :issue:`963492`: The ``recipe.files`` XMLRPC method now ensures that duplicate
  log filenames are filtered out. Previously, if the database contained a duplicate
  log row left over from older bugs, the duplicates would cause the :program:`beaker-transfer`
  to fail when moving the log files.
  (Contributed by Dan Callaghan)

* :issue:`1366098`: The :program:`beaker-provision` daemon now finds and aborts
  any commands which were left in the Running state due to network problems or 
  other error conditions. Previously the commands would be left Running 
  forever. (Contributed by Jon Orris)

* :issue:`1370399`: The :program:`bkr system-delete` command now shows a more meaningful
  message when deleting a nonexistent system.
  (Contributed by Hui Wang)

* :issue:`1252373`: The ``taskactions.files`` XMLRPC method is now documented.
  (Contributed by Dan Callaghan)

* :issue:`1327051`: The :file:`/run/beaker` directory is now created when the
  ``beaker-server`` package is first installed. Previously the directory
  was not created until after rebooting, which would cause the Beaker daemons to
  fail to start up on a fresh installation.
  (Contributed by Dan Callaghan)

* :issue:`1410089`: The location attribute of guest recipe XML now matches the URL
  which Beaker used in generating the kickstart.
  (Contributed by Dan Callaghan)

* :issue:`1174615`: The :program:`bkr job-cancel` command now shows a proper
  message when given an invalid task.
  (Contributed by Dong Wang)

* :issue:`1224848`: The database query used for pagination on the executed tasks page has been optimized
  in order to avoid producing a large temptable in MySQL that can cause errors when loading
  the page.
  (Contributed by Jon Orris)

.. Unreleased bugs:

    * :issue:`1395155`: 500 Internal error message show when inputting wrong user/password
      in Openstack Keystone Trust.
      (Contributed by Róman Joost)
    * :issue:`1390409`: Fixed recipe quick info for OpenStack instances where FQDN is
      not known yet.
      (Contributed by Matt Jia)
    * :issue:`1336272`: dogfood tests can fail because beaker-provision is trying to
      use fence_ilo to power on a non-existent machine.
      (Contributed by Dan Callaghan)
    * :issue:`1361007`: failed to stop Openstack instance
      (Contributed by Matt Jia)
    * :issue:`1389185`: fails to delete OpenStack network with Conflict (HTTP 409) error
      (Contributed by Matt Jia)
    * :issue:`1376650`: downgrade to 23 fails if commands have been run:
      duplicate primary key inserting into activity
      (Contributed by Dan Callaghan)
    * :issue:`969235`: Add version check tests for server utilities.
      (Contributed by Dan Callaghan)
    * :issue:`1361002`: 500 Internal Server Error when using OpenStack
      (Contributed by Matt Jia)
    * :issue:`1410692`:  Fixed a regression in guest recipe XML generation, where
      the guest-related XML attributes were not being correctly injected onto the ``<guestrecipe>``
      element. 
      (Contributed by Dan Callaghan)

.. internal only:
    * :issue:`1225982`


Maintenance updates
-------------------

The following fixes have been included in Beaker 24 maintenance updates.

Beaker 24.1
~~~~~~~~~~~

* :issue:`1422410`: Fixed a regression which caused task uploads to crash with
  ``TypeError`` if the task introduced new excluded releases in its metadata. 
  (Contributed by Dan Callaghan)
* :issue:`1412487`: The :program:`beaker-import` utility now ignores ``src``
  when it appears as an architecture in compose metadata, for example in Fedora 
  25 :file:`.composeinfo`, allowing the import to complete successfully instead 
  of failing. (Contributed by Dan Callaghan)
* :issue:`1422874`: The Beaker web application's last resort error handling for
  failed database rollbacks is more more resilient in out-of-memory conditions. 
  (Contributed by Dan Callaghan)
* :issue:`1412878`: The recipe page now only links to HTTP on the running
  system if the recipe is actually running (or reserved). Previously the link 
  would appear even before the recipe had started or after it was finished, 
  when it didn't make sense. (Contributed by Dan Callaghan)
* :issue:`1425522`: Beaker now sends queries for computing Graphite metrics to
  the "reporting" database connection, if configured. This allows 
  administrators to offload the queries to a read-only database replica. 
  (Contributed by Dan Callaghan)
