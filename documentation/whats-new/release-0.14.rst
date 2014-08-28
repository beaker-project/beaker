What's New in Beaker 0.14?
==========================

The principal feature added in Beaker 0.14 is the introduction of
"submission delegates", completing the
`Enhanced User Groups <../../dev/proposals/enhanced-user-groups.html>`_ 
design proposal.


Migrating to Beaker 0.14
------------------------

Beaker 0.14 is expected to be the last release that supports the old
implicit job sharing model. The legacy mechanism has been superseded by the
:ref:`group-jobs-0.13` feature introduced in Beaker 0.13. Users will need
to switch to using explicitly shared group jobs to allow members of their
groups access to jobs.

Beaker previously permitted the use of task names that contained adjacent
slash characters (``"//"``) or a trailing slash character. To avoid problems
with filesystem path and URL normalisation, this is no longer permitted.

Another change in this release which may impact users that are
experimenting with alternative harnesses *and* using Beaker's guest
recipe feature: the result returned when
:ref:`retrieving the recipe details <lc-api-get-recipe>` for a guest
recipe now embeds the ``<guestrecipe>`` element inside a ``<recipe>``
element rather than providing it directly inside the ``<recipeset>``
element.


Submission delegates
--------------------

Submission delegates are a new feature that enables a job to be submitted on
behalf of another user. Once a user has nominated another user to be
a submission delegate, the submission delegate can submit and manage
jobs on behalf of that user. Jobs submitted by the submission delegate
have access to the same system resources that are available to the job
owner, however they only have access to manage jobs they have submitted.

(Contributed by Raymond Mancy in :issue:`960302`)


Notable enhancements
--------------------

My Group Jobs page
~~~~~~~~~~~~~~~~~~

Beaker 0.13 introduced the "group jobs" feature, which allows users to submit
jobs for a specific group. As part of this feature, the "My Jobs" page was
updated to also include jobs from other users which were submitted for a
group of which you are a member.

However, this made the "My Jobs" page excessively noisy for users who belong
to many groups (or groups which submit a lot of jobs). In this release the
"My Jobs" page has been reverted to its previous behaviour, and a new
"My Group Jobs" page has been introduced which lists jobs submitted for
any groups of which you are a member.

(Contributed by Dan Callaghan in :issue:`984374` and :issue:`984382`)


Access the hypervisor's hostname from a guest recipe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The hypervisor's hostname is now exposed to tasks running in a guest
recipe via the ``HYPERVISOR_HOSTNAME`` environment variable
(when using the default beah test harness).

When returned from the ``simple harness`` API via ``/recipes/<recipe_id>``, the
``guestrecipe`` element is now within a ``recipe`` element (instead of directly
in the ``recipeSet`` element). The ``recipe`` element will contain the value
of the guestrecipe's hypervisor hostname in the ``system`` attribute.

(Contributed by Raymond Mancy in :issue:`887760`.)


Improved console monitoring for RHEL 6 guest recipes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new kickstart snippet has been added that configures ``ttyS0`` and
``ttyS1`` so that a task running on the host system can monitor the
serial console while still collecting the console logs for Beaker.

(Contributed by Gurhan Ozen in :issue:`978419`.)


Fedora based fully virtualised Beaker quick start
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The developer guide now includes instructions that should allow developers
to easily set up their own Fedora based experimental Beaker instance using
a pair of virtual machines on their development system.

While there are still some known compatibility issues when running Beaker
on Fedora 19+ (see :issue:`989902`), this configuration is sufficient to
allow users to submit and run jobs on the test VM.

(Contributed by Amit Saha in :issue:`977269` and :issue:`979211`)


Architecture guide
~~~~~~~~~~~~~~~~~~

Beaker's documentation has previously lacked a good home for explanations
of the concepts behind Beaker's various capabilities, or even a clear
overview of those capabilities.

The introduction of an :ref:`architecture-guide` (distinct from the
existing User, Admin and Developer guides) is intended to address that
limitation. This initial iteration provides a general overview of the
purpose of Beaker and the tools it provides to support that purpose. In
future releases, it will be enhanced with more detailed explanations of
various Beaker components that aren't suited to any of the other guides.

(Contributed by Nick Coghlan in :issue:`955521`)


Security hardening for sensitive data handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Historically, Beaker has assumed a system level security model for
production servers and not taken any specific steps to prevent sensitive
data leaking out through server log files.

To better support the use of log aggregation systems for data analysis,
this policy has now changed, and Beaker aims to ensure sensitive data does
not leak out through these files.

With Beaker 0.14 and later, all Beaker log files should be safe to include
in a log aggregation system without leaking sensitive data.

With prior versions of Beaker, the ``/var/log/beaker/server-debug.*`` logs
(on the main server) and the ``/var/log/beaker/provision.*`` logs (on
the lab controllers) should *not* be included in log aggregation systems.

(Contributed by Dan Callaghan in :issue:`986108` and :issue:`989271`)


Bug fixes and minor enhancements
--------------------------------

A number of other smaller fixes and enhancements have been included in this
release.

* :issue:`862146`: ``bkr --version`` will now print Beaker's version info
* :issue:`961205`: task Makefile targets are now documented
* :issue:`975644`: OS version aliases can once again be updated
* :issue:`963542`: Beaker processes now log via syslog rather than directly
  to disk
* :issue:`859796`: to avoid generation of ambiguous paths, task names are no
  longer permitted to contain adjacent or trailing slash characters
* :issue:`953749`: A system's Power tab now displays an appropriate message
  if the user does not have permission to send power commands, rather than
  appearing blank.
* :issue:`907242`: distro imports now report an appropriate error when the
  distro metadata conflicts with a registered distro alias
* :issue:`972407`: the new task page now gives a more appropriate error when
  no task is supplied for upload
* :issue:`968608`: the Kerberos helper in ``bkr.common`` should now
  renew expired credentials correctly
* :issue:`985174`: License markers for Beaker's code (as opposed to task
  code) have been updated to consistently use the phrase "GPLv2 or later"
  or "GPLv2+" (a couple of locations inadvertently used the "GPLv2" notation)


Maintenance updates
-------------------

The following fixes have been included in Beaker 0.14 maintenance updates.

Beaker 0.14.1
~~~~~~~~~~~~~

* :issue:`990408`: TurboMail is now started in beakerd, so that it does not 
  fail to send notification emails


Beaker 0.14.2
~~~~~~~~~~~~~

Task updates (refer to :ref:`updating-harness-packages` to apply):

* :issue:`1022261`: The inventory task once again handles 390x and
  ppc64 systems (using the ``iasl`` packages published in Beaker's
  harness repositories) (Contributed by Amit Saha)

This maintenance release also backported several fixes and smaller features
from Beaker 0.15 and 0.15.1 to the Beaker 0.14.x series. See the `Beaker
0.15 Release Notes
<http://beaker-project.org/docs/whats-new/release-0.15.html>`__ for more
details on some of these changes.

Provisioning updates:

* :issue:`989924`: Beaker now uses the default authentication configuration
  on all distributions by default. This can be controlled through the new
  ``auth`` setting in the ``ks_meta`` attribute of a recipe specification
  in the job XML. (Contributed by Amit Saha)
* :issue:`1002928`: the ``ntp`` package is no longer removed by default
  (Contributed by Amit Saha)
* :issue:`1002261`: The btrfs technical preview can once again be selected
  as a partition filetype in Red Hat Enterprise Linux 6
  (Contributed by Nick Coghlan)
* :issue:`997629`/:issue:`994677`: Beaker now correctly forces all EFI
  systems to attempt netboot prior to local boot, even if the boot order
  is implicitly switched to prefer local boot during installation. This is
  needed to ensure the system can be automatically reprovisioned after use
  (Contributed by Raymond Mancy)
* :issue:`1006690`: Provisioning Fedora rawhide is now supported
  (Contributed by Amit Saha)
* :issue:`1013414`: When importing the latest RHEL7 distros into Beaker,
  their addon repos will now be correctly added.
  (Contributed by Raymond Mancy)

Automated scheduling failure handling improvements:

* :issue:`977562`: Recipes will now be aborted if there are no candidate
  systems in Automated mode. Previously, affected recipes would remain
  queued indefinitely, even if all candidate systems were configured for
  Manual mode or marked as Broken. (Contributed by Raymond Mancy)
* :issue:`953543`: the external watchdog now fires correctly even if the
  system is stuck in panic loop (Contributed by Raymond Mancy)
* :issue:`954219`: the external watchdog now fires correctly even if the
  system is stuck in an install loop due to an Anaconda failure
  (Contributed by Amit Saha)
* :issue:`1008509`: beaker-provision now kills the entire process group
  for failed power scripts, avoiding problems due to wayward child processes
  in some power control clients (Contributed by Raymond Mancy)

Web UI improvements

* :issue:`990860`: group owners are now identified on the group page for
  all users (making it easier for non-group members to request membership)
  (Contributed by Amit Saha)
* :issue:`920018`: the system list no longer shows systems on disabled
  lab controllers (Contributed by Amit Saha)
* :issue:`988848`: Searching for multiple CPU/Flags entries now gives the
  appropriate results (Contributed by Raymond Mancy)

Other backported fixes:

* :issue:`999967`: The ``bkr job-list`` command once again works with the
  ``python-json`` package on Red Hat Enterprise Linux 5
  (Contributed by Amit Saha)
* :issue:`999733`: Individual recipe sets can now be cancelled over XML-RPC
  (Contributed by Nick Coghlan)
* :issue:`1014623`: We now encode XML received on the client side in utf-8.
  This ensures non ascii characters are rendered properly, and encoding
  errors are avoided. (Contributed by Martin Kyral and Dan Callaghan)
* :issue:`759269`: An empty MOTD no longer causes tracebacks in
  server-errors.log (Contributed by Dan Callaghan)


Beaker 0.14.3
~~~~~~~~~~~~~

Provisioning updates:

* :issue:`967479`: The scheduler now ensures that, when testing a freshly
  imported distro (which may not be available in all labs) as a guest on a
  more stable distro (which *is* available in all labs), the host system will
  only be provisioned in a lab that has both distros available.
  (Contributed by Raymond Mancy)
* :issue:`1012452`: ``rhts-compat`` is now correctly disabled for RHEL7
  recipes that use a custom kickstart (Contributed by Amit Saha)

Client updates:

* :issue:`1027036`: GPLv2+ is now the default task license in beaker-wizard
  (Contributed by Nick Coghlan)
* :issue:`867087`: The new --repo-post workflow option allows a custom repo
  to easily be configured to only be available after initial installation of
  the system (Contributed by Gurhan Ozen and Nick Coghlan)

Test harness updates:

* :issue:`1004381`: The beah test harness no longer emits spurious
  "ERROR: Unhandled error in Deferred" messages after completion of the
  final task in a recipe (Contributed by Amit Saha)


Beaker 0.14.4
~~~~~~~~~~~~~

.. note::

   As an important step in improving Beaker's support for IPv6-only testing,
   the ``beaker-proxy`` daemon now listens on both IPv4 and IPv6 network
   interfaces on the lab controller. The way this is implemented means that
   the lab controller *must* have IPv6 support enabled or the ``beaker-proxy``
   daemon won't start. (If not actually conducting IPv6-only testing, the lab
   controller doesn't need to be externally accessible over IPv6 - it just
   needs to accept ``::`` as designating the "unspecified address", so the
   daemon can listen on all IPv4 and IPv6 interfaces on the server)

Provisioning updates:

* :issue:`1013413`: beaker-import now detects and imports ISO install images
  available in distribution trees, allowing use of the ks_meta"method=nfs+iso"
  option in recipe definitions. Note that some distros may currently still
  require an appropriate explicit "stage2" setting to install via this
  method (see :issue:`846103` for details) (Contributed by Raymond Mancy)
* :issue:`1033032`: A multihost recipe set scheduling error introduced by the
  fix for :issue:`967479` in 0.14.3 that could cause recipe sets to be Aborted
  rather than Queued has been fixed (Contributed by Nick Coghlan)
* :issue:`1030612`: Beaker now preserves all existing EFI boot order entries
  while ensuring the system remains configured to boot from the network by
  default. This avoids a problem where some EFI firmware would incorrectly
  create multiple copies of the default boot entries, along with another
  where some EFI firmware deletes any entries not explicitly listed in the
  boot order (Contributed by Dan Callaghan)
* :issue:`1031876`: Beaker and the default test harness no longer assume
  all EFI firmware will define a BootCurrent variable (Contributed by Dan
  Callaghan)
* :issue:`1029681`: Beaker no longer attempts to run efibootmgr in guest
  recipes, as doing so could break Xen guests on ia64/HVM
  (Contributed by Dan Callaghan)
* :issue:`994635`: Beaker now generates a suitable network boot menu for EFI
  systems (Contributed by Dan Callaghan)
* :issue:`1031999`: Beaker's Anaconda installation monitoring now captures
  ``/tmp/ifcfg.log`` (Contributed by Dan Callaghan)

Test harness updates:

* :issue:`894159`: rhts-sync-block no longer spams the console with
  "rhts-sync-block: <Fault 8002: 'error'> messages" (Contributed by
  Dan Callaghan)
* :issue:`1001304`: The obsolete ControlGroup option has been removed from
  the beah service file (Contributed by Amit Saha)

Documentation updates:

* :issue:`1030172`: the architecture guide now includes an overview of
  the :ref:`bare metal provisioning process <provisioning-process>`
  (Contributed by Dan Callaghan)
* several additional kickstart snippets, including the new ``boot_order``
  snippet added as part of resolving the EFI boot order issues in
  :issue:`1030612`, are now documented (Contributed by Nick Coghlan)

Other updates:

* :issue:`1030909`: the various fixes made to beaker-sync-tasks in Beaker
  0.15 have been backported to Beaker 0.14.4 (Contributed by Nick Coghlan)
* :issue:`1032377` and :issue:`1004622`: several fixes and additions have
  been made to the Beaker installation guide (Contributed by Nick Coghlan)
* :issue:`1032653`: taskactions.task_info() should once again work for
  recipes that were never assigned to a system (Contributed by Dan Callaghan)
