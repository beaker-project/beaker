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

The job page search now defaults to searching based on whiteboard text. You
can also enter a job ID prefixed with "J:" to search for a specific job
instead. (Contributed by Anwesha Chatterjee in :issue:`999933`)

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


Maintenance updates
-------------------

The following fixes have been included in Beaker 25 maintenance updates.

Beaker 25.1
~~~~~~~~~~~

* :issue:`1563072`: Fixed a regression introduced in Beaker 25.0 which caused
  the /systems/by-uuid/.../ipxe-script endpoint to return incomplete URLs. This
  would cause OpenStack instances to fail to boot the installer.
  (Contributed by Róman Joost)
* :issue:`1552401`: Beaker now recognizes more installation failure patterns to
  abort the job during installation.
  (Contributed by Róman Joost)
* :issue:`1557847`: When a user deletes the OpenStack Keystone trust in their
  preferences, Beaker also deletes the trust in Keystone. If this fails, Beaker
  now ignores the error and considers the trust to be deleted. Previously Beaker
  would return a 500 error.
  (Contributed by Róman Joost)
* :issue:`1558776`: Fixed regression introduced in Beaker 25.0 which caused
  beakerd to spew a very large amount of log messages which will cause beakerd
  and rsyslog to consume a lot of CPU.
  (Contributed by Dan Callaghan)
* :issue:`1165960`: Beaker client now provides a reserver-workflow subcommand to
  easily reserve a system.
  (Contributed by Matt Jia)
* :issue:`1558828`: Fixed regression in which beakerd tried to assign a system
  again from a lab controller with not enough systems.
  (Contributed by Dan Callaghan)


Beaker 25.2
~~~~~~~~~~~

* :issue:`1568217`: Fixed regression in beaker-provision which will fail with an
  AttributeError if power commands were queued just before a Beaker 25
  migration. (Contributed by Dan Callaghan)
* :issue:`1568224`: beakerd would fail to generate an email notification for
  jobs in the 'Scheduled' state after Beaker has been upgraded to 25.0. The
  migration has been fixed to include scheduled jobs and add the necessary
  installation row in the database.
  (Contributed by Róman Joost)
* :issue:`1568238`: Fixed regression in the result XML generation for guest
  recipes.
  (Contributed by Dan Callaghan)

Beaker 25.3
~~~~~~~~~~~

* :issue:`1568224`: The online migration in 25.2 did not migrate all
  pending jobs that were missing an installation row. Due to this we
  found an issue with beakerd incorrectly suppressing an exception.
  Mishandling this execption caused an SQL transaction to be commited
  when it should have been rolled back. The end result of this is that
  beakerd would crash due to recipies being in a half provisioned state.
  The recipies have been aborted and the exception handling has been fixed.
  (Contributed by Róman Joost)
* :issue:`1574311`: The update_dirty_job() routine in the scheduler now
  avoids an unnecessary SELECT query. This shaves several seconds off
  each iteration on large Beaker installations.
  (Contributed by Dan Callaghan)
* :issue:`1568648`: The invocation of curl in the generated kickstart would
  not follow redirects, causing the installation to abort if the stage2 image
  was just a HTML file. This has been fixed and curl will follow a redirect
  to download the image.
  (Contributed by Róman Joost)


Beaker 25.4
~~~~~~~~~~~

* :issue:`1573081`: The SQL used by the beakerd scheduler would take
  approximately 30 seconds to find recipe sets to schedule, even if
  there are no valid recipes to find.  The SQL for this has been
  rewritten to use indexes more efficently and as a result query time
  has been reduced to less than a second.
  (Contributed by Dan Callaghan)
* :issue:`1577729`: When MariaDB is configured to be in strict mode, the
  database will throw an error if Activity.field_name is greater than
  40 characters.  The SQL model has been updated to truncate at 40
  characters.
  (Contributed by Róman Joost)
* :issue:`1574772`: This is a partial fix for Beaker recipe performance.
  Beaker would hold an SQL transaction open when processing recipies.
  If beaker has a large set of recipies to process, this open transaction
  would negatively impact database performance due to the overhead of
  the database needing to maintain transaction state.
  (Contributed by Dan Callaghan)


Beaker 25.5
~~~~~~~~~~~

* :issue:`1505207`: Beaker's new job page is using an automatic update mechanism
  which loads JSON data from the Beaker server in intervals. For jobs with many
  recipes, the amount of data can be very big which was putting a lot of load on
  the server when it happened in short intervals. This has been fixed. A new
  request is only sent to the server, if the previous request has responded
  therefore removing any potential for unnecessary load.
  (Contributed by Jacob McKenzie)
* :issue:`1574317`: Beaker's kernel panic detection regular expression which
  triggers on an ``Oops`` word found in the log output has been slightly tweaked.
  We adjusted the expression from ``\bOops\b`` to ``Oops[\s:[]`` to avoid it
  falsely triggering on data with the same word appearing in the log
  output.
  (Contributed by Jacob McKenzie)
* :issue:`1588263`: Beaker now sets ``Auto-Submitted: auto-generated`` and
  ``Precedence: bulk`` headers when it sends automated emails (such as job
  completion notifications). This avoids triggering vacation auto-replies, which
  are meaningless noise for the Beaker administrator.
  (Contributed by Dan Callaghan)
* :issue:`1065202`: The XMLRPC API for registering new recipe log files now
  correctly acquires an exclusive lock on the relevant recipe row. This avoids a
  deadlock which could occur if the scheduler was attempting to update the
  recipe at the same time. Note that the deadlock was harmless, but it would
  produce an error in ``beakerd.log``.
  (Contributed by Dan Callaghan)
* :issue:`1591391`: Beaker now truncates usernames to 60 characters before
  storing them in the activity tables of the database. Previously, when the
  database was using MySQL "strict mode", some HTTP requests would fail with an
  Internal Server Error if the user performing the action had a username longer
  than 60 characters.
  (Contributed by Jacob McKenzie)
* :issue:`1593042`: The beaker-import tool now supports importing RHEL8 Alpha
  composes synced to partner labs.
  (Contributed by Róman Joost)
* :issue:`1586049`: In order to keep backwards compatibility
  with non-strict MySQL deployments, Beaker now coerces the score value to an
  integer similar to what MySQL non-strict is doing. Previously, if tests
  mistakenly reported the score as a non-integer value, Beaker was returning an
  internal server error, because a MySQL database configured in strict mode is
  rejecting the wrong score.
  (Contributed by Róman Joost)
* :issue:`1369590`: Fixed a problem with the LESS stylesheets which would cause
  the application to fail to start if lessc 2.7 is installed.
  (Contributed by Dan Callaghan)

The lshw package in the Beaker harness repositories has also been updated
to incorporate the latest upstream fixes. It is now based on lshw commit 028f6b2
from 14 June 2018.


Beaker 25.6
~~~~~~~~~~~

* :issue:`1619482`: The :program:`anamon` installer monitoring script now works
  correctly on RHEL8 where neither :file:`/usr/bin/python` nor 
  :file:`/usr/bin/python3` exist in the installer image. Previously the script 
  would fail to start and Anaconda logs would not be captured and shown on the 
  :guilabel:`Installation` tab of the recipe page. (Contributed by Jacob 
  McKenzie)
* :issue:`1619969`: The :program:`beaker-repo-update` command now correctly
  verifies checksums after downloading harness packages to the Beaker server, 
  and also correctly discards any incomplete or corrupted packages which exist 
  on disk. Previously, if there was an incomplete or corrupted package already 
  on disk, it would be further corrupted. (Contributed by Dan Callaghan)
* :issue:`1612338`: The ``<disk><sector_size>`` XML element for host filtering
  now correctly filters disks by their logical sector size, as documented. 
  Previously it was filtering on physical sector size instead. (Contributed by 
  Pavel Cahyna)
* :issue:`1600281`: If a task reports a result with a score of more than
  8 digits, the score is now capped at 99999999, to prevent a ``DataError`` 
  when the database is using MySQL "strict mode". This matches the existing 
  behaviour when the Beaker database is MySQL in non-strict mode. (Contributed 
  by Dan Callaghan)
* :issue:`1591244`: Beaker now captures some additional Anaconda logs and
  displays them on the :guilabel:`Installation` tab of the recipe page: 
  :file:`yum.log` on RHEL6, and :file:`dnf.librepo.log`, :file:`hawkey.log`, 
  and :file:`lvm.log` on recent Fedora releases. (Contributed by Matt Tyson)
* :issue:`1607515`: The :program:`beaker-wizard` utility now correctly fills in
  the task Author field if the GECOS (display name) field of the user account 
  running it contains non-ASCII characters. Previously it would crash with 
  a ``UnicodeDecodeError`` exception. (Contributed by Dan Callaghan)

Version 0.7.13 of the Beah test harness has also been released:

* :issue:`1610621`: The RPM package now depends on ``python2-*`` versioned
  package names (``python2-twisted-web`` instead of ``python-twisted-web``, 
  etc) in releases where they are available. Previously Beah was not usable for 
  Fedora 29 recipes because virtual provides for the unversioned package names 
  have been removed from Fedora 29 onwards. (Contributed by Dan Callaghan)
* :issue:`1622756`: Version 0.7.13-3 fixes a packaging mistake introduced in
  0.7.13-1, which would cause Beah services to fail to start on RHEL4. 
  (Contributed by Róman Joost)

Version 2.3 of the :program:`beaker-system-scan` hardware scanning utility has 
also been released:

* :issue:`1609597`: Uses Python 3 on Fedora 29 onwards and RHEL8 onwards.
  (Contributed by Dan Callaghan)
