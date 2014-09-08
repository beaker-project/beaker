What's New in Beaker 0.12?
==========================

Noteworthy changes
------------------

Arguments for ``set_hub`` in workflow commands
++++++++++++++++++++++++++++++++++++++++++++++

If you maintain any third-party Beaker client subcommands or workflows, you 
should update them to pass all keyword arguments to the ``set_hub`` method. 
This is necessary so that the new ``--hub`` option, and any other common 
options added in future, are obeyed::

    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)
        ...

Kickstart sections are terminated for Red Hat Enterprise Linux 6
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Previously, when Beaker generated kickstarts for Red Hat Enterprise Linux 6 the 
``%packages``, ``%pre``, and ``%post`` sections were not terminated with an 
``%end``. Hence, additional kickstart commands specified in the recipe using 
``ks_appends`` were not parsed as commands by the kickstart parser. This has 
now been rectified and hence allows you to specify additional kickstart 
commands using ``ks_appends``.

A consequence of this change is that if you want to specify a post-install 
scriptlet using ``ks_appends``, you will now have to begin a
new ``%post`` section. For example::

    <ks_append>
    %post
    echo 'Custom script begins here'
    %end
    </ks_append>

See bug :issue:`907636` for the background behind this change.

Job status is updated asynchronously
++++++++++++++++++++++++++++++++++++

The beakerd daemon is now responsible for updating job status based on the 
latest state of the tasks in the job. This includes sending notifications and 
returning systems when a recipe finishes.

This change increases throughput for calls made by the harness while running 
a recipe, and eliminates various race conditions which can leave jobs or 
systems in an inconsistent state (see bugs :issue:`807237` and :issue:`715226` 
for details).

However, the job and recipe states shown in Beaker's interface (including 
Status, Result, and progress bars) will lag a small amount behind reality. The 
amount of lag is expected to be less than 20 seconds (the polling interval for 
beakerd). While a job is waiting to be updated its status will appear as 
"Updating…".

Task names are limited to 255 characters
++++++++++++++++++++++++++++++++++++++++

Due to MySQL index size limitations, task names are now limited to 255 
characters.

``readahead`` package is no longer excluded
+++++++++++++++++++++++++++++++++++++++++++

In previous versions, the readahead package was excluded during installation 
for all distros because it is known to `conflict with auditd 
<https://bugzilla.redhat.com/show_bug.cgi?id=561486>`__, but actually it is 
only necessary to turn off readahead collection on Red Hat Enterprise Linux 6.

The ``-readahead`` line no longer appears in ``%packages``, and readahead 
collection is disabled only when provisioning a RHEL6 distro.

Logs are no longer sent to the Beaker server
++++++++++++++++++++++++++++++++++++++++++++

Originally the beaker-proxy daemon forwarded log chunks from the test systems 
to the Beaker server for storage. During the 0.5.x series, the beaker-transfer 
daemon was added, to optionally forward the logs to an external archive server 
instead. In this case the logs would be "cached" on the lab controller (not 
sent to the server) and then moved to the archive server when the recipe set is 
finished.

This "caching" behaviour is now unconditional. That is, logs are always stored 
on the lab controller. This is sufficient for small sites, and is effectively 
the same if the server and lab controller are the same system. If an archive 
server is configured and beaker-transfer is enabled, then logs are moved there.

The ``CACHE`` setting in ``/etc/beaker/labcontroller.conf``, which previously 
controlled this behaviour, no longer has any effect and can be removed.

``beaker-expire-distros`` reports network errors
++++++++++++++++++++++++++++++++++++++++++++++++

The ``beaker-expire-distros`` command runs on the lab controllers to detect 
distro trees which have been removed. Previously, it would consider a tree to 
be "missing" if the root directory of the mirror was accessible but the tree 
itself was not -- even if the cause was a network error or server-side failure.

Now ``beaker-expire-distros`` checks specifically for the protocol errors which 
mean the path does not exist (404 and 410 for HTTP, 550 for FTP). Any other 
errors, including DNS resolution failures, network timeouts, or failed 
requests, are printed to stderr and the command exits. If the 
``--ignore-errors`` option is passed, network errors are suppressed instead and 
``beaker-expire-distros`` continues checking other trees.

If your distro mirror is known to be unreliable (for example, requests time out 
during periods of high load) you may wish to add ``--ignore-errors`` to 
``/etc/cron.hourly/beaker_expire_distros`` in order to avoid cron spam.

New features
------------

Provisional support for alternative harnesses
+++++++++++++++++++++++++++++++++++++++++++++

This release includes provisional support for alternative harnesses. This 
includes a new HTTP API for harnesses to communicate with Beaker, a new result 
type "None", and a mechanism to select a harness other than Beah in generated 
kickstarts. See :ref:`alternative-harnesses` for full details. (Contributed by 
Dan Callaghan in :issue:`915128`.)

New system loan interface and comment field
+++++++++++++++++++++++++++++++++++++++++++

System loans are now granted and returned using an AJAX widget on the system 
page. On top of the existing functionality, a comment field is now available 
for recording comments about loans. See :ref:`loaning-systems` for further 
details. (Contributed by Raymond Mancy in :issue:`733347`.)

Live role environment variables
+++++++++++++++++++++++++++++++

The ``RECIPE_MEMBERS`` environment variable and any other role environment 
variables are now updated at the start of every task. In particular, this makes 
it possible to do multi-host testing between guest recipes and their host. The 
guest FQDNs will be available on the host for tasks executed after the guests 
have finished installing (in most cases, after the 
``/distribution/virt/install`` task). (Contributed by Dan Callaghan in 
:issue:`887283`.)

Disk information in inventory
+++++++++++++++++++++++++++++

The ``/distribution/inventory`` task now collects information about disks 
present in the system and records them in Beaker. The disk information appears 
under the :guilabel:`Details` tab of the system page. You can search disk 
information in the web UI, and you can filter systems by their disks in 
``<hostRequires/>`` using the ``<disk/>`` element. (Contributed by James de 
Vries and Dan Callaghan in :issue:`766919`.)

``<not/>`` element in XML filters
+++++++++++++++++++++++++++++++++

The ``<not/>`` element can be used in ``<hostRequires/>`` and 
``<distroRequires/>`` to negate the meaning of any filter criteria it encloses. 
If it contains multiple filters, they are implicitly AND-ed together.

For example, the following filter matches systems which have a disk whose 
sector size is greater than 512 bytes (even if the same system also has a disk 
whose sector size is *not* greater than 512 bytes)::

    <disk>
        <sector_size op="&gt;" value="512" />
    </disk>

whereas the following filter matches systems which have *no* disks whose sector 
size is 512 bytes::

    <not>
        <disk>
            <sector_size op="=" value="512" />
        </disk>
    </not>

(Contributed by Dan Callaghan.)

Other enhancements
------------------

- The scheduler tries to pick systems with more than one CPU core before 
  systems with only one CPU core, as the latter are rarer. (Contributed by 
  Raymond Mancy in :issue:`824534`.)

- The netboot configuration for a system can be cleared from the
  :guilabel:`Commands` tab on the system page. (Contributed by Raymond Mancy in 
  :issue:`559332`.)

- A new command, ``bkr update-prefs``, lets you update your user preferences in
  Beaker. In this first release, it only supports updating your email address. 
  (Contributed by Qixiang Wan in :issue:`832937`.)

- The ``beaker-sync-tasks`` command is a new server side tool to sync the task
  RPMs on a local Beaker instance with those on a remote Beaker instance. It
  overwrites tasks of the same name on the local instance with that
  from the remote Beaker instance if they are of different
  versions. Tasks which are only present on the remote instance are
  added to the local instance.
  
  See :ref:`copying tasks <sync-tasks>` to learn more about how to use this 
  tool. (Contributed by Amit Saha in :issue:`912205`.)

- The ``bkr job-list`` command no longer prints the number of jobs found. It
  now accepts a ``--format`` option to control its output format. Currently, 
  the two supported formats are ``list`` (newline-separated) and ``json`` (JSON 
  array). The ``list`` format can be used as input to other command line 
  utilities, for example: ``bkr job-list --mine --format list | wc -l`` would 
  print the number of jobs found for the user invoking the command. 
  (Contributed by Amit Saha in :issue:`907658`.)

- Custom repositories are now made available at install time, using the
  Anaconda ``repo`` command in the kickstart, for Red Hat Enterprise Linux 5 
  and Fedora. This was already being done for Red Hat Enterprise Linux 6 and 
  above. (Contributed by Amit Saha in :issue:`902390` and :issue:`912234`.)

- You can now set ``unsupported_hardware`` in kickstart metadata to provision
  systems with Red Hat Enterprise Linux 6 on unsupported hardware. It can be 
  set on a per-system basis in the :guilabel:`Install Options` tab (see 
  :ref:`system-details-tabs`) or in the ``ks_meta`` attribute of the ``recipe`` 
  element (see :ref:`recipes`). Beaker will automatically add the 
  ``unsupported_hardware`` command to the kickstart and provision the system, 
  avoiding the need for manual user intervention during installation. 
  (Contributed by Amit Saha in :issue:`907636`.)

- The ``bkr`` client now accepts a ``--hub`` option (for all subcommands), to
  override the hub URL specified in the configuration file. This can be used to 
  submit jobs against a testing Beaker instance, for example. (Contributed by 
  Dan Callaghan in :issue:`903865`.)

- You can now limit the distro tree import process to specific arches and
  variants, by passing the ``--arch`` and ``--variant`` options to 
  ``beaker-import``. Support for importing trees outside of their compose has 
  also been improved. (Contributed by Raymond Mancy in :issue:`880933`.)

- The beaker-proxy daemon now uses `gevent <http://www.gevent.org/>`_ instead
  of SimpleXMLRPCServer. This means beaker-proxy can efficiently handle many 
  concurrent connections using a single process. Previously, a new handler 
  process was forked for every request. (Contributed by Dan Callaghan.)

- The name prefix for oVirt virtual machines created by Beaker is now
  configurable through the ``guest_name_prefix`` setting. A lab controller can 
  now have multiple oVirt data centers associated with it. (Contributed by Dan 
  Callaghan.)

- oVirt integration is now enabled for Red Hat Enterprise Linux 3 and i386 
  recipes. (Contributed by Qixiang Wan in :issue:`884898` and :issue:`884901`.)

- The special handling for kernel types when importing ``armhfp`` distro trees
  is now activated for ``arm`` distro trees as well. (Contributed by Bill Peck 
  in :issue:`903709`.)

Documentation improvements
--------------------------

- The :ref:`Beaker Makefile <testinfo.desc>` section was updated to describe the ``Provides`` field. 
  (Contributed by Amit Saha in :issue:`910725`.)
- The various job XML–related sections were rearranged into a new page, 
  :ref:`job-xml`. This page now includes examples of searching for specific 
  hardware. (Contributed by Amit Saha in :issue:`887746`.)
- The :ref:`testinfo-releases` section was updated for clarity. (Contributed by 
  Dan Callaghan in :issue:`743579`.)
- The :manpage:`bkr(1)` man page was updated to accurately reflect all the 
  options supported by workflow commands. (Contributed by Amit Saha in 
  :issue:`916351`.)
- Beaker's documentation now includes release notes for each new version. The 
  release notes describe any significant changes, new features, and bug fixes 
  which are included in that release. They also contain upgrade instructions 
  for Beaker administrators, supplanting the previous SchemaUpgrades directory.

Bug fixes
---------

The following bugs were fixed in Beaker 0.12.0:

- :issue:`691666`: guestname attribute of guestrecipe should not be required in job XML
- :issue:`745971`: beaker-wizard should provide 'None' as possible value for attachment download
- :issue:`768381`: No Fedora repos in kickstart 
- :issue:`805791`: Typo in beaker-wizard: MaxLenghtTestName should be MaxLengthTestName
- :issue:`807237`: Job still running when all of its parts are completed
- :issue:`807991`: Unexpected package definition: -readahead
- :issue:`839888`: Leading and trailing whitespace is not stripped in search boxes
- :issue:`855703`: Storing logs on the lab controller should be possible even without an archive server
- :issue:`855716`: beaker-transfer stuck in while loop, when disabling cache with untransferred logs
- :issue:`858944`: "autopick" element is not documented in job XML schema
- :issue:`872187`: Recipes can become deadlocked if a system becomes free during the scheduling loop
- :issue:`874385`: ``beaker_expire_distros`` does not enforce timeouts for HTTP and FTP requests
- :issue:`879991`: Client should allow interrupt power command
- :issue:`880497`: User column is always empty on Recipe Systems page
- :issue:`881387`: Order in which recipes are displayed on the job page depends on their database ID
- :issue:`888959`: ``rhts_post`` snippet doesn't handle duplicate EFI entries
- :issue:`890261`: "like" op in CPU flag filtering does not work
- :issue:`893878`: ``bkr machine-test`` can submit an invalid job if no matching distro is found
- :issue:`903935`: Guest recipes remain stuck in Waiting even though their host recipe is finished
- :issue:`906214`: Check image status before starting VM on RHEV 3.1
- :issue:`906715`: Invalid vmtype (for RHEV 3.1) specified in VirtManager
- :issue:`906803`: ``bkr watchdog-extend`` and ``watchdogs-extend`` commands are too similar
- :issue:`907650`: ``bkr job-list --mine`` lists all jobs if authentication fails
- :issue:`912159`: Changes to beaker.base_mac_addr not taking effect
- :issue:`912242`: Trailing spaces in distro tree URL should be removed
- :issue:`915549`: Task table is missing a unique constraint on 'name' field
- :issue:`915695`: NoSuchElementException is raised for some Selenium tests occasionally
- :issue:`917745`: Internal error (500) when adding system to a group twice
- :issue:`917933`: Users can delete jobs not owned by themselves
- :issue:`920433`: ``createrepo`` output is not captured
- :issue:`922721`: Notify CC list should be visible to non-admins

The following bugs were fixed in Beaker 0.12.1:

- :issue:`889065`: Scheduling deadlock for multihost tests
- :issue:`950922`: Upgrade instructions for 0.12 may lead to a long outage
- :issue:`951283`: Role environment variables have duplicate FQDNs if recipe role and task role are the same
- :issue:`951309`: beaker-provision sometimes runs commands twice
- :issue:`951981`: Cannot import naked distro tree
- :issue:`952948`: CLIENTS role in a guest recipe halts /distribution/install task of host recipe
