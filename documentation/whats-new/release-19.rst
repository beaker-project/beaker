What's New in Beaker 19?
========================

Beaker 19 brings many improvements to the system page. For Beaker 
administrators, the upgrade process has been streamlined with automatic 
database schema upgrades.

Starting with this release, the leading zero has been dropped from Beaker's 
version numbering scheme.

Improved system page
--------------------

In this release the system page has been re-arranged and improved. The aim of 
the improvements is to reduce wasted space, convey information more 
efficiently, and simplify interactions with the page.

Important changes you need to be aware of are listed below. For a complete 
description of all the changes and their background and rationale, refer to the 
:ref:`original design proposal <beakerdev:proposal-system-page-improvements>`.

The new layout relies on browser support for the `CSS3 Flexible Box Layout 
Module <http://www.w3.org/TR/css3-flexbox/>`_. Beaker is tested with Firefox 24 
(which is the oldest supported ESR version of Firefox at the time of writing). 
Older versions of Firefox are not supported and may be unable to render the 
system page properly.

Major page layout changes
~~~~~~~~~~~~~~~~~~~~~~~~~

The system form — the set of fields arranged in two columns at the top of the 
system page — has historically formed the focus of the system page. Over many 
years of development, however, it has grown into a disorganized assortment of 
data, of which only a small amount is relevant for any given workflow on the 
page.

In its place, the system page now has three "quick info boxes". They are 
designed to show the most important facts about the system and to give quick 
access to the most common operations, while occupying a very small amount of 
vertical space. The left-hand box shows a summary of the system's hardware. The 
middle box shows a summary of the system's current usage. The right-hand box 
shows a summary of the system's health.

The interface elements previously contained in the system form will instead be 
shown in tabs below. The previous horizontal tab strip is replaced with 
a vertical list of tabs, to accommodate their increasing number. The tabs have 
also been re-ordered and grouped by theme.

Relocated interface elements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The various fields and interface elements which previously made up the system 
form are now grouped into more appropriate tabs on the page:

* The :guilabel:`Lab Controller`, :guilabel:`Location`, :guilabel:`Lender`, and
  :guilabel:`Kernel Type` fields are part of the :guilabel:`Hardware 
  Essentials` tab.

* The :guilabel:`Hypervisor` field (renamed :guilabel:`Host Hypervisor` for
  clarity), as well as the :guilabel:`Vendor`, :guilabel:`Model`, 
  :guilabel:`Serial Number`, and :guilabel:`MAC Address` fields, are included 
  in the :guilabel:`Hardware Details` tab.

* The :guilabel:`Owner` and :guilabel:`Notify CC` fields are located on a new
  :guilabel:`Owner` tab.

* The :guilabel:`Loan Settings` modal, plus the :guilabel:`Request Loan`
  functionality previously accessible through the :guilabel:`Contact Owner` 
  button, have been moved to a dedicated :guilabel:`Loan` tab.

* The :guilabel:`Condition` and :guilabel:`Type` fields are part of the
  :guilabel:`Scheduler Settings` tab.

* Change a system's FQDN by clicking :guilabel:`Rename` in the page header.

The :guilabel:`Arch(s)` tab, for specifying supported architectures for the
system, has been replaced by the :guilabel:`Supported Architectures` field on 
the :guilabel:`Hardware Essentials` tab.

:guilabel:`Provision` tab always provisions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :guilabel:`Provision` tab now always provisions the system immediately (if 
you have permission to do so). In previous versions of Beaker, the tab would 
sometimes schedule a new job for the system instead of provisioning it 
immediately, depending on the current state of the system.

To provision a system through the scheduler, use the reserve workflow. The 
:guilabel:`Provision` tab now includes a direct link to the reserve workflow 
for the specific system.

Screen scraping scripts will be impacted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The HTML structure of the system page has changed substantially in this 
release. In addition, a number of widgets render their markup entirely in the 
browser and no corresponding HTML appears in the server response. Therefore any 
screen scraping scripts which interact with the system page are likely to be 
impacted.

Since Beaker 0.15 a number of new Beaker client subcommands for manipulating 
systems have been added, to reduce the need for screen scraping scripts. You 
should use these in preference to screen scraping whenever possible:

* :ref:`policy-list <bkr-policy-list>`, :ref:`policy-grant <bkr-policy-grant>`,
  and :ref:`policy-revoke <bkr-policy-revoke>`: for listing, adding, and 
  removing rules from system access policies

* :ref:`loan-grant <bkr-loan-grant>` and :ref:`loan-return <bkr-loan-return>`:
  for granting and returning system loans

* :ref:`system-status <bkr-system-status>` and :ref:`system-modify
  <bkr-system-modify>`: for viewing and setting certain system attributes 
  (currently just owner and condition)

If you have screen scraping scripts whose functionality is not covered by these 
subcommands, please `file an RFE against Beaker 
<https://bugzilla.redhat.com/enter_bug.cgi?product=Beaker&keywords=FutureFeature>`__ 
requesting a new client command exposing the functionality you need.


Manual systems in the Reserve Workflow
--------------------------------------

When the user is browsing systems in the Reserve Workflow, Beaker now also 
offers systems which are in Manual mode (in addition to Automated). If the user 
picks a Manual system it will be reserved using the "forced system scheduling" 
mechanism introduced in Beaker 0.17.

System access policy restrictions will still apply as normal. Users will only 
be offered systems for which they have ``reserve`` permission.

If the user does not pick a specific system, the usual scheduler behaviour will 
continue to apply: only Automated systems will be selected by the scheduler.

(Contributed by Amit Saha in :issue:`1093226`.)


Automatic database schema upgrades
----------------------------------

The :program:`beaker-init` command now supports fully automatic database schema 
upgrades and downgrades using `Alembic <http://alembic.readthedocs.org/>`__. It 
can upgrade Beaker databases from version 0.11 or higher.

(Contributed by Matt Jia and Dan Callaghan in :issue:`682030`.)


Notable changes
---------------

``systemd-readahead`` is disabled in Beaker recipes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker now disables readahead collection on distros with systemd, in the same 
way that the readahead service is disabled on RHEL6. Readahead is not generally 
useful in Beaker recipes because they typically only boot once, and the harness 
interferes with normal data collection.

You can opt out of this behaviour by setting the ``no_disable_readahead`` 
kickstart metadata variable. This will cause Beaker to omit the snippet which 
disables readahead collection.

Workflow commands no longer use ``STABLE``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :program:`bkr` workflow commands no longer filter for distros tagged 
``STABLE`` by default. If your Beaker installation is using the ``STABLE`` tag, 
you can apply the filter explicitly by adding ``--tag=STABLE`` when invoking 
workflow commands.


Other new features and enhancements
-----------------------------------

A new subcommand :program:`bkr system-modify` has been added to the Beaker 
client to modify attributes of existing systems. In this initial release, the 
subcommand can change the system owner and condition. (Contributed by Amit Saha 
and Dan Callaghan in :issue:`1118884`, :issue:`804479`.)

A new system permission ``view_power`` allows users to view and export the 
power settings for a system. System owners can grant this permission to trusted 
users/groups for debugging purposes. (Contributed by Dan Callaghan in 
:issue:`1012174`.)



Task and harness updates
------------------------

Version 4.0-86 of the ``/distribution/virt/install`` task for installing guest 
recipes has been published. The task no longer disables NetworkManager in 
favour of the network initscript on distros where NetworkManager is capable of 
handling bridging (RHEL7 and Fedora). (Contributed by Matt Jia in 
:issue:`1150132`.)

A new task ``/distribution/virt/image-install`` has been published, providing 
experimental support for running guest recipes in VMs booted from disk images 
with cloud-init. Refer to the :ref:`task documentation 
<virt-image-install-task>` for more details. (Contributed by Matt Jia in 
:issue:`1108455`.)

Version 0.7.8 of the Beah test harness has been released, fixing an issue with 
the harness service configurations for systemd which could cause systemd to 
enter an inconsistent state. (Contributed by Dan Callaghan in 
:issue:`1147807`.)

Version 1.5 of the :program:`beaker-system-scan` utility has been released, 
fixing a regression which affects systems whose :file:`/boot` volume is on 
a mapped block device. (Contributed by Amit Saha in :issue:`1148174`.)


Bug fixes
---------

The following user interface bugs/RFEs are solved by the system page 
improvements in this release:

* :issue:`619335`: The :guilabel:`Provision` tab should offer a way of
  filtering distros, to make it easier to find the desired distro.
* :issue:`692777`: The system page should show how long a system has been
  reserved.
* :issue:`880724`: The reserve workflow does not filter systems by lab
  controller, even if you select a specific lab controller when filtering for 
  distro trees.
* :issue:`884399`: When using the :guilabel:`Provision` tab, any install
  options given are applied on top of the default install options for that 
  system and distro. As a consequence, if you edit the pre-populated install 
  options on the :guilabel:`Provision` tab to *remove* a default option, it 
  will have no effect.
* :issue:`980352`: No error message is shown if a validation error occurs when
  editing a system (for example, when the condition report value is too long).
* :issue:`999444`: The :guilabel:`Loan Settings` button appears when editing
  a system, but clicking it does nothing.
* :issue:`1009323`: If a user has no permission to edit a system, clicking the
  :guilabel:`Edit system` button or the :guilabel:`Change` button for notify cc 
  redirects the user back to the system list, instead of to the original system 
  page.
* :issue:`1011284`: The :guilabel:`Loan Settings` button disappears after
  returning an existing loan.
* :issue:`1011293`: The loan settings modal offers to return a loan even when
  none exists.
* :issue:`1020107`: After changing loan settings and closing the loan settings
  modal, the system page does not reflect the new state of the system. In 
  particular, if a user loans the system to themselves they should then be 
  permitted to take the system, but the :guilabel:`Take` button does not 
  appear.
* :issue:`1037280`: The meaning of the :guilabel:`Hypervisor` field on the
  system page is not clear.
* :issue:`1059535`: When saving changes on the :guilabel:`Power Config` tab,
  all fields are recorded in the system activity as being changed, even if they 
  were not actually changed.
* :issue:`1062086`: When using the reserve workflow, if the user selects
  a combination of options which cannot be satisfied by any systems, Beaker 
  warns about the situation but then schedules the job anyway.
* :issue:`1062706`: The procedure for "taking" an Automated system is awkward
  and requires too many steps.
* :issue:`1070036`: When saving changes on the :guilabel:`Power Config` tab, if
  a validation error occurs all fields are cleared and the values are lost.
* :issue:`1134689`: Under some circumstances when saving changes on the
  :guilabel:`Access Policy` tab, a rule is recorded as removed and added 
  multiple times for no reason.

A number of other bug fixes are also included in this release:

* :issue:`1160513`: Fixed a JavaScript ``TypeError`` which would occur when
  viewing the system page for a system whose access policy does not contain any 
  rules. (Contributed by Dan Callaghan)
* :issue:`891827`: The :program:`bkr` workflow commands no longer use the
  STABLE distro tag by default, since it does not exist in default Beaker 
  installations. (Contributed by Dan Callaghan)
* :issue:`1142714`: The :program:`bkr job-submit` command now reads job XML
  from stdin when no positional arguments are given. (Contributed by Dan 
  Callaghan)
* :issue:`1032881`: The :program:`beaker-import` command now has a man page.
  (Contributed by Amit Saha)
* :issue:`1142532`: Server-side memory usage has been reduced in code paths
  which create activity records. In particular, this fixes a MemoryError which 
  can occur on large lab controllers when :program:`beaker-provision` is 
  restarted after being killed uncleanly. (Contributed by Dan Callaghan)
* :issue:`802641`: Deleting of lab controllers is now much faster and more
  memory efficient. Previously, attempting to delete a lab controller would 
  time out in very large labs. (Contributed by Dan Callaghan)
* :issue:`1069438`, :issue:`1061955`: Fixed a number of minor database schema
  inconsistencies between freshly created databases and existing upgraded 
  databases, caused by mistakes in old release notes. (Contributed by Dan 
  Callaghan)
* :issue:`1160091`: Kickstart templates have been tweaked to avoid a bash
  syntax error in case the administrator has defined a custom 
  ``readahead_sysconfig`` or ``virt_console_post`` snippet with no content. 
  (Contributed by Dan Callaghan)
* :issue:`1129059`: The notification e-mail sent when a system is reserved with
  ``<reservesys/>`` now includes a link to the recipe, and includes more useful 
  information when the recipe is running on OpenStack. (Contributed by Dan 
  Callaghan)

.. not reporting the following bugs in unreleased versions:
   :issue:`1145867`
   :issue:`1154887`
   :issue:`1144196`
   :issue:`1145864`
   :issue:`1144203`
   :issue:`1145479`
   :issue:`1152887`
   :issue:`1144190`
   :issue:`1144193`
   :issue:`1144205`
   :issue:`1144195`
   :issue:`1165489`
   :issue:`1163540`

.. these are dev details that are not worth reporting, listed here to keep the 
   scripts happy:
   :issue:`1138496`
   :issue:`1124804`
   :issue:`1072336`
   :issue:`1014438`


Maintenance updates
-------------------

The following fixes have been included in Beaker 19 maintenance updates.

Beaker 19.1
~~~~~~~~~~~

* :issue:`1162513`: Beaker now adds a PPC PReP Boot partition for recipes using
  custom partitioning on ``ppc64le`` distros. Previously it was only defined 
  for ``ppc`` and ``ppc64`` distros, leading to installation failures on 
  ``ppc64le`` distros. (Contributed by Dan Callaghan)
* :issue:`1172450`: Beaker now adds the ``--leavebootorder`` option to the
  ``bootloader`` kickstart command on ``ppc64le`` distros. Previously it was 
  only added for ``ppc`` and ``ppc64`` distros, which caused the boot order to 
  left in an incorrect state after provisioning a ``ppc64le`` distro. 
  (Contributed by Amit Saha)
* :issue:`1014695`: The :program:`bkr` workflow commands now accept
  :option:`--job-owner <bkr --job-owner>`. Submission delegates can use this 
  option to submit jobs on behalf of other users. (Contributed by Dan 
  Callaghan)
* :issue:`1118523`: The :program:`bkr list-systems <bkr system-list>` command now accepts
  :option:`--host-filter <bkr system-list --host-filter>`. This option has the 
  same functionality as the :option:`--host-filter <bkr --host-filter>` option 
  for :program:`bkr` workflow commands. (Contributed by Dan Callaghan)
* :issue:`1131429`: By default :program:`beaker-wizard` now suggests excluding
  RHEL4 and RHEL5 on newly created tasks. (Contributed by Dan Callaghan)
* :issue:`902299`: :program:`beaker-wizard` now strips the word "EMBARGOED"
  from bug summaries when suggesting the task name. (Contributed by Martin 
  Kyral)
* :issue:`1165754`: :program:`beaker-wizard` now correctly escapes backticks in
  shell commands appearing in the generated Makefile, so that they are not 
  evaluated by the shell when make is run. (Contributed by Dan Callaghan)
* :issue:`854229`: The ``swapsize`` kickstart metadata variable now correctly
  sets the size of the swap partition. Previously it was undocumented and did 
  not work in all cases. (Contributed by Dan Callaghan)
* :issue:`745560`: The :program:`beaker-init` utility is now capable of
  converting an existing user account into an admin. (Contributed by Dan 
  Callaghan)
* :issue:`1102617`: The special ``admin`` group is no longer allowed to be
  deleted. (Contributed by Matt Jia)
* :issue:`949855`: Beaker now correctly handles XML host filters which use
  requirements of the form :samp:`<device op="!=" driver="{drivername}"/>`. 
  (Contributed by Dan Callaghan)
* :issue:`1162451`: When a recipe is scheduled with ``<hostRequires
  force=""/>`` on a Manual system, and the system is already reserved, the 
  recipe will remain queued until the system becomes free. Previously Beaker 
  would erroneously consider the queued recipe to be "dead" and abort it. 
  (Contributed by Dan Callaghan)
* :issue:`1163721`: Fixed a display issue with the system page when the
  browser's minimum font size is larger than 14px. (Contributed by Dan 
  Callaghan)
* :issue:`1161373`: Fixed a number of issues which would cause excessive error
  messages to appear on the system page under some circumstances. (Contributed 
  by Dan Callaghan)
* :issue:`1140912`: Beaker now returns a more descriptive error message when an
  invalid username is given in the ``user=""`` attribute of the ``<job/>`` 
  element when submitting a job. (Contributed by Dan Callaghan)
* :issue:`1167164`: When syntactically invalid XML is passed to :option:`bkr
  list-systems --xml-filter <bkr system-list --xml-filter>`, the command now
  prints a concise error message instead of an HTML error page. (Contributed by
  Dan Callaghan)
* :issue:`1073266`: Improved the wording of error messages when the lab
  controller daemons fail to start. (Contributed by Dan Callaghan)
* :issue:`1009377`: The :option:`--help <bkr --help>` output for :program:`bkr
  policy-grant` and :program:`bkr policy-revoke` now lists all possible
  permission values. (Contributed by Dan Callaghan)
* :issue:`1142591`: The ``beaker-lab-controller`` package now correctly
  depends on ``syslinux``. This allows Beaker to automatically copy 
  :file:`pxelinux.0` into the TFTP root directory for convenience in new Beaker 
  installations. (Contributed by Dan Callaghan)

.. dev implementation detail that is not worth reporting: :issue:`980340`

Beaker 19.2
~~~~~~~~~~~

* :issue:`1163466`: The :program:`beaker-provision` daemon now generates
  netboot configuration files for Petitboot, the boot loader used in some 
  recent IBM Power systems. (Contributed by Amit Saha)
* :issue:`1169293`: Usage reminder e-mails now include a header
  ``X-Beaker-Notification: usage-report`` to aid in mail filtering. 
  (Contributed by Matt Jia)
* :issue:`1175118`: The :program:`beaker-import` command now correctly imports
  the "Everything" repo for Fedora 21. This fixes an issue which would cause 
  Fedora 21 jobs to fail with unsatisfied dependencies. The distro must be 
  re-imported for the fix to take effect. (Contributed by Amit Saha)
* :issue:`1174279`: Reverted a change in Beaker 19.0 which caused NTP services
  not to be enabled for guest recipes. Clock syncing is now enabled in all 
  recipes by default. Additionally, guest recipes are now configured so that 
  their hardware clock is assumed to be in UTC, as provided by the host. 
  (Contributed by Matt Jia)
* :issue:`1157348`: Beaker no longer requires that a cached harness repo exists
  for the recipe when using the experimental "contained harness" feature. In 
  that case the job submitter is responsible for ensuring suitable harness 
  packages are available. (Contributed by Amit Saha)
* :issue:`1173402`: Removed references to running Beah inside a container, as
  part of the experimental "contained harness" feature. This never worked 
  properly due to limitations of Beah. Restraint is the recommended harness 
  inside containers. (Contributed by Amit Saha)
* :issue:`1174786`: Fixed an issue with the kickstart snippet for handling
  ``grubport=`` which would cause the GRUB ``menu.lst`` symlink to be 
  overwritten. (Contributed by Dan Callaghan)
* :issue:`1173362`: Beaker now prevents the admin from setting an OS major's
  alias to the same name or alias as another OS major. (Contributed by Dan 
  Callaghan)
* :issue:`1173368`: Beaker no longer accepts the empty string as an OS major
  name or distro name. (Contributed by Matt Jia)
* :issue:`963042`: The lab controller daemons now properly enforce a 120-second
  timeout for connections to the Beaker server. Previously the connect timeout 
  did not take effect for ``https://`` connections. (Contributed by Matt Jia)
* :issue:`1173446`: The :guilabel:`Provision` tab on the system page now always
  shows a link to the Reserve Workflow. (Contributed by Dan Callaghan)

Beaker 19.3
~~~~~~~~~~~

* :issue:`856687`: Beaker client workflow commands accept a new option
  :option:`--ks-append <bkr --ks-append>`, for appending additional commands to 
  the kickstart. (Contributed by Matt Jia)
* :issue:`1124140`: The documentation now covers the :doc:`JSON APIs for
  systems <../../server-api/http>` added since Beaker 0.15. (Contributed by Dan 
  Callaghan)
* :issue:`1183239`: Fixed incorrect query generation when a recipe's host
  requirements contain an ``<arch/>`` filter inside an ``<or/>`` element. 
  Previously these filters would trigger a runaway database query which could 
  consume all temp table space. (Contributed by Dan Callaghan)
* :issue:`1182545`: Fixed handling of date formats when searching systems by
  date added or date inventoried. (Contributed by Matt Jia)
* :issue:`1171936`: Beaker now detects and reports invalid sh-style syntax in
  kickstart metadata: for example, an unterminated ``'`` quote. (Contributed by 
  Dan Callaghan)
* :issue:`1193746`: Fixed an issue with redirects in JSON collection APIs,
  where query string parameters would be discarded. (Contributed by Dan 
  Callaghan)

.. not worth reporting: :issue:`1064634`: Point users at Stack Overflow as an additional help resource

Version 4.0-86 of the /distribution/virt/install task for guest recipes has 
also been released:

* :issue:`1180595`: Updated to support the ppc64 architecture. (Contributed by
  Ján Stanček)
* :issue:`1187266`: Removed spurious RPM dependency on ``virt-manager``, which
  is not available on all architectures and releases. (Contributed by Dan 
  Callaghan)

A new core task, :ref:`/distribution/command <command-task>` version 1.1-4, has 
also been released.

.. the above is :issue:`1018013`
