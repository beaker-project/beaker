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

Beaker 24.2
~~~~~~~~~~~

* :issue:`1415309`: The JUnit XML results produced by Beaker is now more
  consistent with the format produced by JUnit itself. This fixes some issues 
  which prevented the Jenkins JUnit reporter from importing the results. 
  (Contributed by Bill Peck)
* :issue:`1420106`: The jobs grid now renders the whiteboard as Markdown
  instead of treating it as plain text, to match the behaviour of the job page. 
  (Contributed by Bill Peck)
* :issue:`1422385`: The :program:`beaker-wizard` utility is now compatible with
  python-bugzilla 2.0. (Contributed by Dan Callaghan)
* :issue:`1404054`: The :program:`beakerd` daemon no longer attempts to run
  (pointless) data migrations on an empty, freshly created database. 
  (Contributed by Matt Jia)
* :issue:`1426745`: Eliminated some redundant ``COUNT()`` queries in the
  scheduler. (Contributed by Dan Callaghan)
* :issue:`1426764`: Adjusted the ordering of scheduler steps to avoid giving
  too much bias to the ``update_dirty_jobs`` routine. (Contributed by Dan 
  Callaghan)

Version 4.0-93 of the ``/distribution/virt/install`` and version 1.0-7 of the 
``/distribution/virt/image-install`` tasks have also been released:

* :issue:`1425793`: The :program:`wait4guesttasks` utility now correctly waits
  for tasks only in the *guest* recipe. Previously it would incorrectly return 
  early if the *host* recipe also contained a completed task with the same 
  name. (Contributed by Jan Tluka)

Beaker 24.3
~~~~~~~~~~~

* :issue:`1442147`: A new, Python 3 compatible version of the :program:`anamon`
  monitoring script is now used when the installation environment contains 
  Python 3, for example on Fedora 26. (Contributed by Johnny Bieren)
* :issue:`1442146`: The kickstart template for Fedora now correctly passes the
  "mirrorlist" URL for the updates repo. Previously it passes the Metalink URL 
  instead, which is not supported in Anaconda starting from Fedora 26. 
  (Contributed by Dan Callaghan)
* :issue:`1438666`: Beaker now fills in the ``HOSTNAME`` parameter for the
  ``/distribution/inventory`` task when it schedules a hardware scan job for 
  a system. This avoids problems in case the system is not assigned the correct 
  fully-qualified domain name by DHCP. (Contributed by Jonathan Toppins)
* :issue:`1335394`: The :option:`bkr update-inventory --dry-run` option now
  works correctly when a hardware scan job is already running. Previously it 
  would refuse to produce a dry run of the job definition. (Contributed by 
  Jonathan Toppins)
* :issue:`1386074`: Under some circumstances the JSON API for system details
  would return an incorrect value for the `id` key, which caused the web UI to 
  report an error: "System access policy not specified". This has been 
  corrected. (Contributed by Dan Callaghan)
* :issue:`1234323`: The :program:`bkr` workflow commands no longer reject
  other host filtering options when combined with the :option:`--machine
  <bkr --machine>` option. This is necessary when using 
  :option:`--systype=Prototype <bkr --systype>` to select prototype systems. 
  (Contributed by Dan Callaghan)

Version 4.0-94 of the ``/distribution/virt/install`` and version 1.0-8 of the 
``/distribution/virt/image-install`` tasks have also been released:

* :issue:`1440647`: The ``--nographics`` and ``--noautoconsole`` options are
  now passed to :program:`virt-install` on aarch64. (Contributed by Artem 
  Savkov)
* :issue:`1441751`: The :program:`logguestconsoles` program now correctly
  handles the case where the guest console log file is truncated by qemu. 
  (Contributed by Jakub Racek)
* The ``/distribution/virt/install`` now compares the OS release numerically
  instead of lexicographically. Previously the task would consider Fedora 
  releases to be too old to support KVM. (Contributed by Johnny Bieren)

Version 4.73 of the ``rhts`` test development and execution library has also 
been released:

* :issue:`1417988`: If a task tries to upload a non-existent log file using
  :program:`rhts-report-result` or :program:`rhts-submit-log`, the command will 
  exit with an error instead of an unhandled exception, to avoid triggering 
  abrt. (Contributed by Dan Callaghan)

Beaker 24.4
~~~~~~~~~~~

* :issue:`1420471`: The boot menu for EFI GRUB now excludes distros which are
  known not to support EFI, namely Red Hat Enterprise Linux 3, 4, and 5, and 
  any distro for the i386 architecture. (Contributed by Dan Callaghan)
* :issue:`1464120`: The ``<hypervisor/>`` element in host filter XML now works
  correctly with systems which have no hypervisor. Previously this filter would 
  incorrectly exclude systems when used with ``op="like"`` or ``<not/>``. 
  (Contributed by Dan Callaghan)
* :issue:`1470959`: Fixed a scheduling deadlock which could occur in certain
  circumstances when two multi-host recipe sets both require the same candidate 
  systems. (Contributed by Dan Callaghan)
* :issue:`1344889`: Fixed an error when using the :program:`bkr` client with
  Python 2.7.7+ through an HTTP proxy. (Contributed by Dan Callaghan)
* :issue:`1457606`: The :program:`beaker-watchdog` daemon no longer crashes
  when reporting a panic for a job which has non-ASCII characters in the 
  whiteboard. (Contributed by Dan Callaghan)
* :issue:`1043772`: Beaker now returns a more informative error message if you
  attempt to create an LDAP group but the server is not configured to use LDAP. 
  (Contributed by Anwesha Chatterjee)
* :issue:`1469345`: Beaker's JSON API now returns a more informative error
  message if you attempt to create a group with a name longer than 255 
  characters. (Contributed by Anwesha Chatterjee)
* :issue:`1358619`: The watchdog time remaining shown on the recipe page is now
  correctly updated when you extend the reservation. (Contributed by Anwesha 
  Chatterjee)
* :issue:`1412897`: The post-install script for reporting the system hostname
  now works correctly on RHEL5 when the system has no valid FQDN. (Contributed 
  by Dan Callaghan)
* :issue:`1472070`: The distros grid search for "Tag is not" now works
  correctly. Previously it would fail with 500 Internal Server Error. 
  (Contributed by Dan Callaghan)
* :issue:`1473067`: The :program:`bkr` workflow commands now print a more
  informative error message if you have not selected any tasks to run in your 
  job, or if you have tried to select tasks for a package which does not exist. 
  (Contributed by Anwesha Chatterjee)
* :issue:`1473135`: The checkboxes for tracking recipe reviewed state on the
  job page are now disabled when you have not logged in. Previously the 
  checkboxes were not disabled but clicking them would do nothing. (Contributed 
  by Anwesha Chatterjee)
* :issue:`1360589`: Recipes are now automatically marked as reviewed if they
  finish while the recipe page is open in the browser. Previously they would 
  only be marked as reviewed if you refreshed the page. (Contributed by Anwesha 
  Chatterjee)
* :issue:`1340566`: Fixed a server-side error message which would occur if the
  :program:`beaker-watchdog` daemon detected a kernel panic for a Reserved 
  recipe. (Contributed by Anwesha Chatterjee)

Version 4.0-95 of the ``/distribution/virt/install`` and version 1.0-9 of the 
``/distribution/virt/image-install`` tasks have also been released:

* :issue:`1465788`: The task now restarts the libvirtd service to ensure its
  virtlogd feature is disabled. This is necessary with QEMU 2.9.0 and newer. 
  (Contributed by Jan Stancek)

Beaker 24.5
~~~~~~~~~~~

* :issue:`1500142`: Fixed an issue causing some parts of the recipe page to be
  re-rendered once per second. In particular, the panel which showed system 
  information was re-rendered once per second, making it impossible to select 
  or copy the hostname. (Contributed by Anwesha Chatterjee)
* :issue:`1497021`: The :program:`bkr job-modify` command now correctly
  modifies the priority of group jobs. Previously it would fail with 500 
  Internal Server Error when the user making the request was not the original 
  job submitter. (Contributed by Dan Callaghan)
* :issue:`1498804`: The systems grid now correctly handles searches where the
  ``value`` parameter is missing from the query string, which would occur in 
  certain edge cases. (Contributed by Dan Callaghan)
* :issue:`1497881`: Beaker no longer allows you to add deleted users to groups,
  give deleted users ownership of systems, or lend systems to deleted users. 
  (Contributed by Dan Callaghan)
* :issue:`1498374`: Beaker now transfers ownership of system pools when a user
  account is deleted, in the same way it transfers ownership of systems. 
  Additionally, it no longer allows you to give deleted users ownership of 
  system pools. (Contributed by Dan Callaghan)
* :issue:`1499646`: Beaker now correctly evaluates ``<not/>`` host filters when
  considering whether a recipe can be run in OpenStack. Previously, use of 
  ``<not/>`` would always preclude the recipe from running in OpenStack. 
  (Contributed by Dan Callaghan)
* :issue:`1501671`: The :program:`rhts-power` command for Beaker tasks now
  works correctly, regardless of the system access policy. Previously the 
  command would fail with ``InsufficientSystemPermissions`` unless the system's 
  access policy granted ``control_power`` permission to all users (which was 
  the default in Beaker prior to 0.15). (Contributed by Dan Callaghan)
