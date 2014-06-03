What's New in Beaker 0.17?
==========================

Beaker 0.17 includes two new scheduler features, as well as support for theming 
Beaker's web UI, and experimental integration with OpenStack for dynamically 
creating VMs.

Harness independent system reservation
--------------------------------------

A new XML element ``<reservesys/>`` added to a recipe will reserve the system 
after all tests have been completed. The duration to reserve the system can 
optionally be given using the ``duration`` attribute. It is expressed in 
seconds. The default duration is 86400 seconds (24 hours).

Unlike the ``/distribution/reservesys`` task, which remains fully supported, 
this new mechanism reserves the system even if the recipe execution is aborted 
by the external watchdog timer or due to a kernel panic or installation 
failure.

Refer to the :ref:`system-reserve` section for more information.

(Contributed by Amit Saha in :issue:`639938`.)

Force system scheduling
-----------------------

It is now possible to force Beaker's scheduler to choose a specific system for 
a recipe, regardless of whether the system's condition is set to Automated, 
Manual or Broken.

A new attribute ``force`` has been added to the ``<hostRequires/>``
element. For example::

    <hostRequires force="my.host.example.com" /> 

will force the job to run on ``my.host.example.com``.
The ``force`` attribute is mutually exclusive with any other existing host 
selection criteria; the ``<hostRequires/>`` element must not contain any other 
content in this case.

Access policy restrictions still take effect when the ``force`` attribute is 
used. The job owner must have ``reserve`` permission on the system in question 
in order to reserve it through the scheduler.

The :program:`bkr machine-test` command now accepts a new option 
:option:`--ignore-system-status <bkr machine-test --ignore-system-status>`
which uses this feature. This option makes it possible to test a system or 
update its hardware details even if its condition is set to Manual or Broken.

(Contributed by Amit Saha in :issue:`851354` and :issue:`1093224`.)

Theming the web interface
-------------------------

Administrators can apply custom styles and markup to Beaker's web interface. 
For example, you can make it match a common look-and-feel for your 
organization, or add extra links to site-specific resources.

See :doc:`../../admin-guide/theming` for details about how to use this feature.

(Contributed by Dan Callaghan in :issue:`1012224`.)

OpenStack as dynamic virtualization backend
-------------------------------------------

Beaker's previous experimental oVirt integration has been ported to use 
OpenStack instead.

When OpenStack integration is enabled, Beaker will attempt to create a new
virtual machine for each recipe when it is scheduled. If creating the virtual 
machine fails, Beaker will fall back to using the regular hardware
pool for that recipe. Recipes with hardware requirements in
``<hostRequires/>`` which cannot be satisfied by a virtual machine are
excluded from this process.

This feature is currently considered experimental and has a number of 
limitations: guest consoles are not logged; VM building can cause a scheduling 
bottleneck; and OpenStack credentials must be stored in Beaker's database. 
Therefore it is currently not recommended to use this feature in production 
Beaker instances.

Refer to :ref:`openstack` for information about how to configure this feature 
in your Beaker instance.

(Contributed by Dan Callaghan in :issue:`1040239`.)

Notable changes
---------------

"Removed" systems are no longer shown in search results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Systems whose condition is set to "Removed" are only searchable from a new page 
(:menuselection:`Systems --> Removed`). Removed systems are no longer included 
on any other system search pages. Before this change, removed systems matching 
the search criteria would also be listed along with other matching systems.

As a consequence, ``Removed`` is no longer an accepted value for the 
``System/Status`` field on system search pages.

Removed systems are also excluded from the output of :program:`bkr 
list-systems` by default. A new option :option:`--removed <bkr-list-systems 
--removed>` can be given in order to list removed systems.

(Contributed by Amit Saha in :issue:`1000092`.)

Workflow commands ignore system selection options when ``--machine`` is given
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the :option:`--machine <bkr --machine>` option is given, any other host 
selection criteria (:option:`--hostrequire <bkr --hostrequire>`, 
:option:`--systype <bkr --systype>`, :option:`--keyvalue <bkr --keyvalue>`, or 
:option:`--random <bkr --random>`) are ignored and a warning is printed to 
stderr.

(Contributed by Amit Saha in :issue:`1095026`.)

LDAP TLS certificate checking is no longer disabled
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In previous versions the Beaker web application disabled TLS certificate 
checking for LDAP connections. The certificate checking behaviour is now 
inherited from the system-wide OpenLDAP configuration. By default OpenLDAP 
requires a trusted certificate on all connections.

If your Beaker site is using LDAP integration you should ensure that your LDAP 
directory's CA is trusted by adding it to the system-wide OpenSSL trust store, 
or by setting the ``TLS_CACERT`` option in :file:`/etc/openldap/ldap.conf` 
appropriately.

If necessary, TLS certificate checking can be disabled system-wide in OpenLDAP 
by setting the ``TLS_REQCERT`` option in :file:`/etc/openldap/ldap.conf`. See 
:manpage:`ldap.conf(5)` for details.

(Contributed by Dan Callaghan in :issue:`962639`.)

``beaker`` package renamed to ``beaker-common``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``beaker`` package has been renamed to ``beaker-common``. This package 
contains common Python modules and is required by all other Beaker packages. 
The new package Provides and Obsoletes the old package name, so yum will 
replace it during upgrade without intervention. However, any scripts which 
refer to the ``beaker`` package explicitly should be updated.

(Contributed by Dan Callaghan in :issue:`1072143`.)

Other new features and enhancements
-----------------------------------

Job cancellations and changes to retention settings are now tracked in the job 
activity log, visible at the top of the job page. (Contributed by Matt Jia in 
:issue:`995012`.)

A new :ref:`kickstart metadata variable <kickstart-metadata>` 
``dhcp_networks``, similar to the existing ``static_networks`` variable, allows 
configuring additional network devices to start on boot. (Contributed by Dan 
Callaghan in :issue:`920470`.)

The :option:`--hostrequire <bkr --hostrequire>` workflow option now accepts 
arbitrary XML snippets. This makes it possible to express more complex host 
requirements, for example using ``<and/>`` and ``<or/>`` combinations. 
(Contributed by Dan Callaghan in :issue:`1014693`.)

A new lab controller API resource :http:get:`/recipes/(recipe_id)/watchdog` 
allows scripts on the test system to determine how much time is left on the 
watchdog timer. (Contributed by Dan Callaghan in :issue:`1093052`.) 

The :program:`beaker-provision` daemon copies the PXELINUX boot loader image 
into place automatically if it does not exist. As a result, new Beaker 
installations can run recipes on x86 BIOS-based systems immediately. Previously 
all boot loader images had to be fetched manually or by using the 
:program:`cobbler get-loaders` script. (Contributed by Dan Callaghan in 
:issue:`866765`.)

Task and harness updates
------------------------

Version 4.0-81 of the ``/distribution/virt/install`` task has been released, 
with improved logic for manipulating the ``--network`` option in the guest 
arguments. The task no longer injects a ``bridge:`` parameter when a ``type=`` 
parameter is given. This makes it possible to use the non-default network 
device types supported by :program:`virt-install`, including macvtap devices. 
(Contributed by Andy Gospodarek in :issue:`1086285`.)

.. add beah 0.7.5 release here?

    Version 0.7.5 of the Beah test harness has been released, with the 
    following fixes:

    * :issue:`1077115`

    * ``python-hashlib`` is no longer required. This fixes some issues when the
      test system is running in FIPS mode. (Contributed by Marian Csontos in 
      :issue:`707623`.)

Bug fixes
---------

A number of bug fixes are also included in this release.

* :issue:`1092758`: Fixed a regression preventing upload of tasks with
  ``Architectures: aarch64``. (Contributed by Dan Callaghan)
* :issue:`1066269`: Fixed a regression affecting the :program:`bkr job-watch`
  command when watching an individual recipe or task. (Contributed by Dan 
  Callaghan)
* :issue:`1073280`: Fixed a regression in the
  :option:`--distro <bkr-task-list --distro>` option to the :program:`bkr 
  task-list` command. (Contributed by Dan Callaghan)
* :issue:`1087727`: The :program:`bkr policy-list` command now authenticates to
  the Beaker server instead of making an anonymous request, in case the system 
  is not visible to anonymous users. (Contributed by Dan Callaghan)
* :issue:`1100008`: The device tree path is no longer hardcoded in the AArch64
  boot loader configuration. A custom device tree can be supplied using the 
  ``devicetree`` :ref:`kernel option <kernel-options>`. By default no device 
  tree is configured. (Contributed by Bill Peck)
* :issue:`1064710`: Beaker now prevents multiple lab controllers from sharing
  a single user account. Previously the administrator could create such 
  a configuration, but it would cause errors when the lab controller daemons 
  authenticated to Beaker. (Contributed by Dan Callaghan)
* :issue:`1095010`: Beaker no longer enforces uniqueness of user e-mail
  addresses. This corrects an issue where Beaker would not allow an LDAP 
  account to log in if another existing account had the same e-mail address. 
  (Contributed by Dan Callaghan)
* :issue:`997830`: Usernames consisting only of whitespace characters are no
  longer accepted. (Contributed by Dan Callaghan)
* :issue:`1101402`: If createrepo terminates uncleanly during a task upload,
  Beaker cleans up the temporary work directories left behind, in order to 
  prevent subsequent task uploads from failing. (Contributed by Dan Callaghan)
* :issue:`1072192`: Completed tasks with no results are now correctly displayed
  in the job and recipe progress bars. (Contributed by Dan Callaghan)
* :issue:`1085703`: Deleting a group now works correctly when the group is
  referenced in a system access policy. (Contributed by Amit Saha)
* :issue:`1086505`: LDAP username lookups are encoded as UTF-8.
  (Contributed by Dan Callaghan)
* :issue:`1022411`: The :program:`bkr task-details` command shows a more
  informative error when an unrecognized task name is given. (Contributed by 
  Amit Saha)
* :issue:`1086506`: The :guilabel:`Access Policy` tab on the system page shows
  a more informative error when an unrecognized username is given. (Contributed 
  by Matt Jia)
* :issue:`998374`: Beaker shows a more informative error when the administrator
  attempts to add a new lab controller with the same FQDN as an existing lab 
  controller. (Contributed by Dan Callaghan)
* :issue:`967684`: Beaker shows a more informative error when attempting to add
  a non-existent system to a group. (Contributed by Amit Saha)
* :issue:`978225`: Beaker shows a more informative error when attempting to
  delete a group that has already been deleted. (Contributed by Amit Saha)
