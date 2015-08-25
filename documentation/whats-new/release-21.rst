What's New in Beaker 21?
========================

Beaker 21 simplifies the process for system owners to run hardware scans on 
their Beaker systems, reducing it to a single click or CLI command.
This release also includes an improved version of the 
:program:`beaker-system-scan` tool, providing broader hardware support and more 
accurate hardware information for Beaker systems.


Simplified hardware scanning
----------------------------

The :guilabel:`Hardware Details` tab on the system page shows Beaker's record 
of the hardware in a system, including memory, CPU, and devices. The data on 
this page is populated by running the ``/distribution/inventory`` task on the 
system, usually through the
:option:`--inventory <bkr machine-test --inventory>` option to the 
:program:`bkr machine-test` command.

For system owners and other users with permission to reserve a system, the 
:guilabel:`Hardware Details` tab now includes a :guilabel:`Scan` button which 
triggers a hardware scan with a single click.
When a hardware scan is requested, Beaker will select the best available distro 
family and architecture which is compatible with that system, and schedule 
a job to provision it and run the hardware scan when the system is free.

The simplified hardware scanning functionality is also available from the 
command line with the new :program:`bkr update-inventory` command. Refer to 
:ref:`bkr update-inventory <bkr-update-inventory>` for details.

(Contributed by Amit Saha in :issue:`846185` and :issue:`1121462`.)


Hardware scanning using lshw
----------------------------

Version 2.0 of the :program:`beaker-system-scan` tool has also been released. 

The new version of :program:`beaker-system-scan` uses `lshw 
<http://lshw.ezix.org/>`_ to scan and identify hardware in a system, and then 
sends the details back to Beaker's inventory. It now supports all architectures 
and distros, and in many cases the data it collects is more accurate than 
previous versions.

In order to make lshw usable for Beaker's hardware scanning, the Beaker 
development team reported and submitted patches for a large number of bugs and 
enhancements:

* `#562 <http://www.ezix.org/project/ticket/562>`__: VirtIO disks
* `#615 <http://www.ezix.org/project/ticket/615>`__: logical sector size for disks
* `#623 <http://www.ezix.org/project/ticket/623>`__: DASD on IBM S/390
* `#658 <http://www.ezix.org/project/ticket/658>`__: IBM S/390 CPU capability descriptions
* `#685 <http://www.ezix.org/project/ticket/685>`__: model names for IBM POWER
* `#688 <http://www.ezix.org/project/ticket/688>`__: missing PCI storage classes, hints in XML output
* `#691 <http://www.ezix.org/project/ticket/691>`__: Plug ’n Play devices
* `#692 <http://www.ezix.org/project/ticket/692>`__: IBM Virtual I/O devices
* `#693 <http://www.ezix.org/project/ticket/693>`__: IBM S/390 devices
* `#694 <http://www.ezix.org/project/ticket/694>`__: use memory hotplug to determine total size
* `#695 <http://www.ezix.org/project/ticket/695>`__: DIMM information on IBM JS20
* `#696 <http://www.ezix.org/project/ticket/696>`__: read SMBIOS data from :file:`/sys/firmware/dmi/tables/`
* `#697 <http://www.ezix.org/project/ticket/697>`__: SMBIOS 3.0
* `#690 <http://www.ezix.org/project/ticket/690>`__: incorrect integer sizes in device tree parsing on some platforms
* `#668 <http://www.ezix.org/project/ticket/668>`__: compilation failure with glibc 2.5 (RHEL5)
* `#698 <http://www.ezix.org/project/ticket/698>`__: "x86-64" capability should not be present on aarch64 systems
* `#699 <http://www.ezix.org/project/ticket/699>`__: incorrect number of physical CPUs on aarch64
* `#700 <http://www.ezix.org/project/ticket/700>`__: incorrect handling of multiple memory arrays in SMBIOS data
* `#701 <http://www.ezix.org/project/ticket/701>`__: buffer signedness issue in SCSI inquiry
* `#702 <http://www.ezix.org/project/ticket/702>`__: buffer size off by one in SCSI inquiry

(Contributed by Dan Callaghan, Amit Saha, James de Vries, and Matt Jia in
:issue:`541294`, :issue:`896302`, :issue:`902567`, and associated bugs.)


Other new features and enhancements
-----------------------------------

The :program:`bkr watchdog-extend` command now accepts "taskspec" arguments of 
the form ``R:123`` or ``T:123`` to specify the watchdog to be extended. It also 
accepts system FQDNs as arguments, which will extend the watchdog of the recipe 
running on the given system. The existing argument format (task ID without 
``T:`` prefix) is also accepted for backwards compatibility. (Contributed by 
Matt Jia in :issue:`1103582`.)

A new XML element ``<diskspace/>`` can be used in ``<hostRequires/>`` to filter 
on the total size of all disks in the system. This augments the existing disk 
size filter which applies to individual disks in the system. (Contributed by 
Matt Jia in :issue:`1187402`.)

A new :ref:`kickstart metadata variable <kickstart-metadata>` ``no_autopart`` 
causes the default ``autopart`` command to be suppressed in the kickstart. You 
can set this variable if you want to supply custom partitioning commands in 
a ``<ks_append/>`` section of your recipe. (Contributed by Matt Jia in 
:issue:`1198881`.)

Beaker's :ref:`Graphite integration <graphite>` now includes metrics for 
"dirty" jobs count, and number of queued and running power commands. 
(Contributed by Dan Callaghan in :issue:`1173069`.)


Notable changes
---------------

The way Beaker computes the overall status of jobs, recipe sets, and recipes 
has been changed so that Aborted take precedence over Cancelled, and Cancelled 
takes precedence over Completed. If some tasks in a recipe are Completed and 
others are Cancelled or Aborted, the overall status of the recipe will now be 
Cancelled or Aborted, not Completed. Similarly, if some recipes in a job are 
Completed and others are Cancelled or Aborted, the overall status of the job is 
now shown as Cancelled or Aborted, not Completed. (Contributed by Dan Callaghan 
in :issue:`714937`.)

In recipes using Fedora, the official Fedora yum repos configured by the 
``fedora-release`` package will now be disabled. This ensures that the yum 
repos available after installation match the yum repos used during 
installation, and also makes it possible to provision older Fedora releases 
where the official Fedora yum repos have been deleted. (Contributed by Matt Jia 
in :issue:`1202075`.)

When uploading a task RPM, unrecognized fields in :file:`testinfo.desc` are now 
silently ignored instead of causing the upload to be rejected. (Contributed by 
Dan Callaghan in :issue:`1226443`.)


Harness updates
---------------

Version 0.7.9 of the Beah test harness and version 4.67 of the ``rhts`` test 
execution library have been released.

On distros without systemd the harness is now more resilient to failures when 
writing to :file:`/dev/console`. On distros with systemd the harness no longer 
writes to :file:`/dev/console` directly, instead it relies on systemd's journal 
to capture its logging output and display it to the console.

The ``rhts-sync-block``, ``rhts-test-checkin``, and ``rhts-test-update`` 
scripts now avoid writing messages to :file:`/dev/console` directly for the 
same reason.

On distros with systemd the harness services now also depend on 
``network-online.target`` to ensure the network is up before they are started, 
regardless of how the network is configured.

(Contributed by Dan Callaghan in :issue:`1188664` and :issue:`967502`.)


Task updates
------------

Version 1.12-2 of the ``/distribution/install`` task has been published. The 
:file:`anaconda.coverage` log file produced by Anaconda is now uploaded along 
with other log files. (Contributed by Alexander Todorov in :issue:`1248304`.)

Version 4.0-89 of the ``/distribution/virt/install`` task for installing guest 
recipes has been published. It now obeys the kernel options specified for the 
guest recipe. (Contributed by Jan Stancek in :issue:`1236691`.)


Bug fixes
---------

A number of bug fixes are also included in this release:

* :issue:`1252503`: Fixed a regression in Beaker client 20.2 which would cause
  :program:`bkr system-release` to exit successfully even though it had not 
  released the system. (Contributed by Matt Jia)
* :issue:`1253103`: Beaker's disk records for systems are now properly updated. 
  Previously, old disk entries would be left behind in some cases when a disk was 
  removed or changed. (Contributed by Dan Callaghan)
* :issue:`1213225`: The :program:`beaker-repo-update` tool no longer attempts
  to fetch harness packages for distros which do not exist in any Beaker lab. 
  This avoids the situation where Beaker's database may contain references to 
  obsolete or incorrect distro names which have no corresponding harness 
  packages, causing unnecessary WARNING messages to be displayed. (Contributed 
  by Matt Jia)
* :issue:`1195558`: Fixed a corner case in ``<reservesys/>`` handling which
  could cause a recipe to become reserved instead of cancelled when a user 
  cancels it. (Contributed by Dan Callaghan)
* :issue:`1210540`: The :program:`beaker-watchdog` daemon no longer attempts to
  expire the watchdog for "dirty" jobs. This avoids a potential crash under 
  pathological circumstances in which beakerd is taking a very long time to 
  process dirty jobs. (Contributed by Matt Jia)
* :issue:`1198914`: Due to an earlier bug in the logic for system deletion, the
  database may contain orphaned rows in the ``system_access_policy`` table not 
  referenced by any system. Such orphaned rows will be cleaned up by 
  a migration script. (Contributed by Matt Jia)
* :issue:`1211465`: Beaker is now compatible with Alembic 0.7, which is
  included in EPEL7. (Contributed by Matt Jia)
* :issue:`653317`: Due to the changes in :program:`bkr watchdog-extend`
  described above, the error message shown when the user supplies an invalid task 
  ID is now clearer. (Contributed by Matt Jia)

.. unreleased bugs on develop:
   * :issue:`1249923`: receive 500 internal error when extending the watchdog for an already finished recipe (Contributed by Matt Jia)

.. unreleased bugs in beaker-system-scan lshw branch, and/or implementation details:
   * :issue:`1213683`: [lshw] type "multimedia" should be "AUDIO" (possibly)
   * :issue:`1213195`: beaker-system-scan doesn't recognize compaq smart array disks
   * :issue:`1212291`: [lshw] missing some devices
   * :issue:`1212311`: [lshw] missing mainframe devices on S/390
   * :issue:`1213685`: [lshw] 32-bit x86 should be i386, not i686
   * :issue:`1212287`: [lshw] beaker-system-scan does not populate driver field for any(?) devices
   * :issue:`1212294`: [lshw] reports some USB host controllers as type "bus" instead of "USB"
   * :issue:`1213679`: [lshw] VIRT_IOMMU key-value is wrong
   * :issue:`1212281`: [lshw] x86 cpu flags are missing "lm" and have "fpu_exception" and "x86-64"
   * :issue:`1213680`: [lshw] does not determine FORMFACTOR
   * :issue:`1212289`: [lshw] missing subsys ids for some devices
   * :issue:`1212288`: [lshw] does not distinguish between SCSI and IDE devices
   * :issue:`1212285`: [lshw] beaker-system-scan does not determine system vendor and model correctly
   * :issue:`1212284`: [lshw] cpu vendor is "Intel Corp." instead of "GenuineIntel"
   * :issue:`1212295`: [lshw] type "display" should be "VIDEO"
   * :issue:`1213688`: [RFE] lshw should report physical memory size on POWER systems which expose it in device tree
   * :issue:`1212310`: [beaker-system-scan] cpu flags are duplicated on S/390 with multiple CPUs
   * :issue:`1223115`: [lshw] inventory task fails on mustang with KeyError on procCpu.tags['hardware']
   * :issue:`1212307`: [beaker-system-scan] misidentifies cpu information on ia64

.. harness repo administrivia:
   * :issue:`1250335`: no released busybox in beaker repos for rhel-7.2 arch64
