What's New in Beaker 25?
========================

Beaker 25 adds support for provisioning arbitrary distro trees, Anaconda's 
``liveimg`` command, collecting device firmware versions, and many other new 
capabilities.

Custom distros
--------------

Beaker now allows you to provision any arbitrary distro tree for your recipe, 
even if it has not been "imported" by a Beaker administrator.

In your job XML, use the new ``<distro/>`` element to specify the distro to be 
installed in your recipe. Unlike the traditional ``<distroRequires/>`` element, 
which applies your filter criteria to select a distro tree from Beaker's distro 
library — the new ``<distro/>`` element must contain all of the necessary 
metadata for Beaker to provision your custom distro. For example::

    <recipe ...>
        <distro>
            <tree url="http://lab.example.com/distros/MyCustomLinux1.0/Server/x86_64/os/"/>
            <initrd url="pxeboot/initrd"/>
            <kernel url="pxeboot/vmlinuz"/>
            <arch value="x86_64"/>
            <osversion major="RedHatEnterpriseLinux7" minor="4"/>
            <name value="MyCustomLinux1.0"/>
            <variant value="Server"/>
        </distro>
        ...
    </recipe>

(Contributed by Anwesha Chatterjee in :issue:`911515`.)

Firmware version for devices
----------------------------

Beaker now tracks the firmware version (if known) of each device in the system, 
including the version of the system firmware (BIOS) itself. The version 
information is shown in a new column on the :guilabel:`Devices` tab of the 
system page.

(Contributed by Shawn Doherty and Jonathan Toppins in :issue:`1162317`.)

Installation using Anaconda ``liveimg`` command
-----------------------------------------------

Beaker now supports installations which use the Anaconda ``liveimg`` command, 
to populate the installed system from a pre-built image rather than by 
installing RPM packages. This makes it possible to run Beaker recipes using the 
Red Hat Virtualization Host (RHVH) product.

(Contributed by Yuval Turgeman in :issue:`1420600`.)

Filter systems by supported distro family
-----------------------------------------

A new XML host filter has been added, which matches systems that are compatible 
with a particular distro family. For example, in the ``<hostRequires/>`` 
element of your job XML you can use the following filter::

    <system>
        <compatible_with_distro
            osmajor="RedHatEnterpriseLinux7"
            osminor="4"
            arch="x86_64" />
    </system>

to select a system which is compatible with RHEL7.4. Beaker will always select 
a system which is *also* compatible with the distro being provisioned in your 
recipe. You can use this if your recipe provisions RHEL6 but then tests 
upgrading to RHEL7, for example.

(Contributed by Dan Callaghan in :issue:`1387795`.)

Other new features and enhancements
-----------------------------------

A new command :program:`bkr job-comment` lets you comment on recipe sets, 
recipe tasks, and results. (Contributed by Blake McIvor in :issue:`853350`.)

If a task uses exclusions in the Release field of its metadata (for example, 
``Releases: -Fedora21`` to exclude Fedora 21), Beaker now stores this in the 
database as a list of excluded releases as expected.
Previously, it would be represented in the database as an *exclusive* list of 
every *other* distro family known to Beaker, which would produce incorrect 
results when a new distro family appeared in Beaker.
Note that this change only takes effect when a new version of the task is 
uploaded. The metadata for existing tasks will not be automatically updated. 
(Contributed by Dan Callaghan in :issue:`800455`.)

The Architectures field of task metadata now also accepts exclusions (for 
example, ``Architectures: -x86_64`` to exclude x86_64). Previously, exclusions 
were not accepted in this field and were rejected with a validation error. 
(Contributed by Dan Callaghan in :issue:`670149`.)

Beaker now sends email notifications to system owners when their system is 
loaned or returned. The notification is only sent when some *other* user 
performs the action. The new notification type is enabled by default for new 
users. Existing users can opt in to these notifications on their preferences 
page. (Contributed by Dan Callaghan in :issue:`996165`.)

The :guilabel:`Notes` tab of the system page has been re-designed and improved, 
to address some usability issues. (Contributed by Dan Callaghan in 
:issue:`1016409`.)

A new system-wide permission "change_prio" has been defined. If the Beaker 
administrator grants this permission to a group, users in the group are allowed 
to change the priority of any queued Beaker job (including other users' jobs). 
Previously this capability was only allowed for the undocumented, hardcoded 
group name "queue_admin". (Contributed by Dan Callaghan in :issue:`1159105`.)

A new kickstart metadata variable ``beah_no_console_output`` has been added. 
When this variable is defined, the Beah test harness will be configured to 
suppress its debugging messages which are normally printed to the console. 
Messages from other sources are unaffected. This variable has no effect when 
the recipe is using a harness other than Beah. (Contributed by Dan Callaghan in 
:issue:`1410799`.)

The :guilabel:`Excluded Families` tab of the system page now has a button 
labeled :guilabel:`Exclude All`, which will pre-select all distro families to 
be excluded. (Contributed by Shawn Doherty.)

Beaker now has a favicon. (Contributed by Dan Callaghan.)

Notable changes
---------------

This release removes support for Beaker's original group sharing model for 
jobs, which allowed any group member to have full control over any jobs 
submitted by any other members of the group. This "implicit job sharing" 
behaviour was deprecated in Beaker 0.15 and disabled by default in Beaker 22.
In previous releases the ``beaker.deprecated_job_group_permissions.on`` setting 
could be used to enable the old, deprecated behaviour. This setting is now 
ignored.
(Contributed by Dan Callaghan.)

Beaker now passes the ``network --hostname`` kickstart option to Anaconda, so 
that the system hostname always matches the expected FQDN as it is known to 
Beaker. Previously, when this option was not supplied, Anaconda would leave the 
hostname unset causing systemd to set the hostname from DHCP. On systems with 
multiple NICs this would cause the hostname to randomly vary depending on which 
interface came up first.
(Contributed by Dan Callaghan in :issue:`1346068`.)

When a system owner changes the access policy on their system, newly added or 
deleted policy rules are recorded in the system activity record. Previously, 
the rules would be represented in the form ``<grant view to Some Group>`` where 
"Some Group" is the *display* name, not the group name. For consistency with 
other parts of Beaker's web UI, and to make the records more easily 
machine-readable, the rules are now represented in the form 
``Group:somegroup:view`` where "somegroup" is the *group* name.
(Contributed by Dan Callaghan in :issue:`967392`.)

If a recipe uses custom partitioning (``<partitions/>`` element), Beaker now 
uses the ``reqpart`` kickstart command if the distro supports it, instead of 
explicitly creating platform-specific partitions.
(Contributed by Dan Callaghan in :issue:`1230997`.)

Provisioning S/390 guests now uses FTP instead of TFTP for fetching the kernel 
and initramfs images, to work around a limitation in the z/VM TFTP client which 
cannot handle files larger than 32MB. This requires a corresponding update to 
the ``zpxe.rexx`` script. Beaker administrators can restore the previous 
behaviour of using TFTP if necessary, by setting ``ZPXE_USE_FTP=False`` in 
:file:`labcontroller.conf`.
(Contributed by Dan Callaghan in :issue:`1322235`.)

The scheduler now keeps track of newly released systems and assigns them to the 
next suitable queued recipe, if one exists. Previously the scheduler 
continually polled for queued recipes which have matching free systems.
This refactoring improves the scheduler's efficiency in cases where there are 
many queued recipes, and also eliminates some corner cases relating to matching 
queued recipes which have guest recipes.
(Contributed by Dan Callaghan in :issue:`1519589`.)

Beaker's internal database representation of how jobs are deleted has been 
changed. Beaker now distinguishes between *deletion* of a job, which is 
triggered explicitly by a job owner or implicitly when a job reaches its expiry 
time — versus *purging* of a job, which is an automated process in Beaker to 
clean up associated database records and log files for deleted jobs. When 
upgrading to Beaker 25.0, any old deleted jobs which erroneously still have log 
files stored in Beaker will be marked for purging again, so that they are 
properly cleaned up.
(Contributed by Dan Callaghan in :issue:`1337789`.)

Bug fixes
---------

A number of bug fixes are also included in this release:

* :issue:`1425290`: Version 0.7.12 of the Beah test harness has been released,
  with numerous improvements and clarifications to the log messages produced 
  while the harness is running a recipe. (Contributed by Dan Callaghan)
* :issue:`1538906`: The pattern to detect kernel Oops messages now matches
  a broader variety of messages, including some Oops messages on 64-bit ARM 
  kernels which previously went undetected. (Contributed by Róman Joost)
* :issue:`1491658`: Beaker now accepts non-ASCII characters in the name part of
  the Owner field of task metadata. Previously, uploading such a task would be 
  rejected with an error indicating that the Owner was invalid. (Contributed by 
  Dan Callaghan)
* :issue:`1504527`: The :program:`beaker-watchdog` daemon now correctly handles
  non-ASCII characters appearing in the console output of OpenStack instances. 
  (Contributed by Dan Callaghan)
* :issue:`1510710`: The kickstart snippet to handle custom partitioning
  (``<partitions/>`` element) now correctly includes an EFI system partition on 
  x86 EFI machines which are configured to boot GRUB2 (that is, having 
  ``NETBOOT_METHOD=grub2`` key-value). Previously, the code only handled 
  systems booting EFI GRUB 0.97 with the ``NETBOOT_METHOD=efigrub`` key-value. 
  (Contributed by Dan Callaghan)
* :issue:`1189432`: When a system owner adds a new supported architecture on
  the :guilabel:`Essentials` tab of the system page, the :guilabel:`Provision` 
  tab is now correctly updated to reflect the new architecture. Previously it 
  was necessary to refresh the page to see the new options. (Contributed by 
  Anwesha Chatterjee)
* :issue:`1212578`: The ``method=`` kickstart metadata variable is now obeyed
  when the ``manual`` variable is also defined. Previously, the ``method=`` 
  variable would be ignored in some cases. (Contributed by Dan Callaghan)
* :issue:`1415104`: The :program:`bkr` command now terminates with exit status
  141 (128+SIGPIPE) when stdout is a pipe and the pipe is prematurely closed. 
  Previously this would cause an unhandled exception. (Contributed by Dan 
  Callaghan)
* :issue:`1412488`: The :program:`beaker-expire-distros` and
  :program:`beaker-pxemenu` lab controller commands now work correctly if 
  a distro has been imported using https:// URLs instead of http:// URLs. 
  (Contributed by Anwesha Chatterjee)
* :issue:`1470933`, :issue:`1470496`: The :program:`bkr group-members` and
  :program:`bkr group-create` commands have been updated to use the newer JSON 
  API for groups added in Beaker 22.0, instead of XMLRPC. (Contributed by 
  Anwesha Chatterjee)
* :issue:`1379519`: The ``openstack_region.ipxe_image_id`` database column is
  now stored as BINARY, instead of the TEXT representation of the UUID value. 
  (Contributed by Anwesha Chatterjee)
* A number of database schema integrity constraints have been fixed to be
  consistent with Beaker's data model:
  :issue:`859785`,
  :issue:`1393170`,
  :issue:`1393173`,
  :issue:`1393174`,
  :issue:`1393181`,
  :issue:`1393182`,
  :issue:`1393183`,
  :issue:`1393185`,
  :issue:`1393186`,
  :issue:`1393191`.
  (Contributed by Dan Callaghan)
