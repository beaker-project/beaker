What's New in Beaker 0.15?
==========================

The principal feature added in Beaker 0.15 is
"system access policies", the initial phase of the
`Access Policies for Systems
<../../dev/proposals/access-policies-for-systems.html>`__
design proposal. As part of providing the user friendly policy editor,
this release also includes a major update to the main web UI.


System access policies
----------------------

Access policies are a new, more flexible mechanism for controlling who can
access a Beaker system. Access policies replace the existing access controls
for systems, based on the :guilabel:`Shared` flag and the system's group
memberships.

The new policy mechanism is accessible through the :program:`bkr` command line
client and the new :guilabel:`Access Policy` tab in the system web UI and
allows systems owners to grant users and groups specific privileges over
systems. The available permissions are:

* Reserving the system (directly or through the scheduler)
* Issuing power and netboot commands to the system (even when not the current
  user)
* Loaning the system to themselves
* Loaning the system to others (as well as returning loans and manual
  reservations on behalf of other users)
* Editing the system details (including switching between Manual and
  Automated operation)
* Editing the system access policy (the system owner can always edit the
  system access policy)

As part of these changes, the restriction previously preventing unprivileged
users from sharing systems they own with all other users of that Beaker
instance has been removed.

For more details on using the new access policy mechanism, refer to:

* :ref:`system-access-policies` (Beaker User Guide)
* :manpage:`bkr-policy-grant(1)`
* :manpage:`bkr-policy-revoke(1)`

Note that the new Beaker client commands require Python 2.6 or later, and
are thus not supported on Red Hat Enterprise Linux 5.

(Contributed by Dan Callaghan and Nick Coghlan in :issue:`994984`)

.. versionchanged:: 0.15.1

   Beaker 0.15.0 included a more restrictive version of these changes.


Default power command and netboot configuration permissions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In previous Beaker releases, any logged-in user was permitted to issue power
commands and clear the netboot configuration for any system, even when they
were not the current user of that system. This legacy behaviour is preserved
in the access policy for existing systems when migrating to Beaker 0.15.

However, system owners can now remove the legacy rule from their system's
access policy if desired, limiting the ability to issue power commands and
clear the netboot configuration to the current user of the system, Beaker
administrators and those users and groups explicitly granted this permission
by the system access policy. This is the default for new systems added in
Beaker 0.15 or later.


Migrating to Beaker 0.15
------------------------

This section highlights changes which may require adjustments to other tools
and processes when migrating from Beaker 0.14 to Beaker 0.15.

Implicit job sharing is disabled by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, Beaker 0.15 no longer supports the old implicit job sharing
model, which has been superseded by the :ref:`group-jobs-0.13` feature
introduced in Beaker 0.13. Users will need to switch to using explicitly
shared group jobs to allow members of their groups access to jobs.

If this change in behaviour causes problems for an existing installation,
the legacy sharing behaviour can be re-enabled in the server configuration
(see :ref:`enable-legacy-permissions-0.15`).


Disable install failure detection to use the ``manual`` ks_meta variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users can set the ``manual`` ks_meta variable in a recipe definition to
request that most of the kickstart settings be omitted. This will result
in Anaconda prompting for user input, which will be interpreted as an
installation failure by default in Beaker 0.15.3 and later versions.

When setting the ``manual`` ks_meta variable in Beaker 0.15.3 and later, it
is also necessary to disable the
:ref:`installation failure monitoring <disable-install-failure-detection>`.


Manual reservations of Automated systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Manually reserving Automated systems now requires that a loan to the relevant
user be put in place first. The data migration rules from earlier versions
*do not* automatically grant the "loan_self" permission to users - they only
grant the ability to reserve the system, either through the scheduler if the
system is in Automated mode, or directly if it is in Manual mode.

Users that were previously using this workflow may either switch to using
the Reserve Workflow to reserve the system through the scheduler, or else
request that the system owner (or another user with the ability to edit
the relevant system access policy) to grant the "loan_self" permission.


Updates to supported queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SQL filtering criteria to determine if a system is available for use
by all users of a given Beaker instance has changed from "the system is
marked as shared and is not in any system groups" to "the system
access policy grants the 'reserve' permission to all users of the instance".

This `update to an affected supported query
<https://github.com/beaker-project/beaker/blob/master/Server/bkr/server/reporting-queries/machine-hours-by-user-arch.sql>`__
shows how to change the filtering criteria to check the new
``system_access_policy`` and ``system_access_policy_rule`` tables to
determine if a system is shared with all users.


Utilisation graph removed
~~~~~~~~~~~~~~~~~~~~~~~~~

The utilisation graph (previously accessible by selecting
:menuselection:`Reports --> Utilisation Graph` from the menu) has been
removed in this version of Beaker. The graph was very expensive to render
(impacting other operations on the server) and was unusably slow on large
Beaker installations.

Beaker's :ref:`Graphite integration <graphite>` provides a faster, more
flexible alternative for visualizing historical performance of a Beaker
installation. Additional data mining possibilities are available through
the :ref:`supported queries <reporting-queries>` mechanism.


Notable changes
---------------


Changes to authentication configuration when provisioning systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Previously, Beaker configured system authentication to use MD5 hashes
on all distributions other than Red Hat Enterprise Linux 6. This implicit
configuration has now been removed so that the default for every
distribution is used instead.

Additionally, users may now specify a specific authentication configuration
using the ``ks_meta`` XML attribute in their recipe specification. For
example::

    <recipe ks_meta="auth='--enableshadow --enablemd5'">

(Contributed by Amit Saha in :issue:`989924`)


The ntp package is no longer excluded by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To avoid interfering with tasks which require ``ntp``, the package is no
longer excluded when ``chrony`` is available and explicit clock
synchronisation was requested (Beaker's default provisioning behaviour
unless ``no_clock_sync`` is specified in the kickstart metadata).

However if both ``chrony`` and ``ntp`` are installed, the ``ntpd`` service
is still automatically disabled to prevent conflicts with ``chronyd``.

(Contributed by Amit Saha in :issue:`1002928`)


Web UI enhancements
~~~~~~~~~~~~~~~~~~~

To support the development of the new editor interface for system access
policies, the main web UI has been upgraded to be based on the
`Flask <http://flask.pocoo.org/>`__ web framework, using
`Bootstrap <http://getbootstrap.com/>`__ as the basis for the CSS styling.

This update also provides several enhancements to the display of data
tables, with the total item count displayed above the table rather than
below, and the first and last page always being accessible through the
pagination links.

System notes are also now rendered as HTML using Markdown, rather than
displayed in ``<pre/>``. That means notes can take advantage of
Markdown syntax for formatting, including hyperlinks
(which are written as ``[link text](link URL)``).

A number of minor UI issues have also been addressed, including adoption
of a clearer name for the search options toggle, elimination of rounding
issues affecting display of progress bars and correct handling of time
zones when displaying root password effective dates.

(Contributed by Dan Callaghan and Raymond Mancy in :issue:`988678`,
:issue:`589294`, :issue:`820775`, :issue:`630645`, :issue:`660633`,
:issue:`839468` and :issue:`1008331`)


Group ownership indicated in read only view
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every group member's ownership status is now indicated in the group's
read-only view. Previously, group owner status was only visible to
owners of the group and Beaker administrators, making it difficult to
know who to contact to request membership in a group.

(Contributed by Amit Saha in :issue:`990860`)


Clarified "Take", "Schedule Provision", and "Provision" in the web UI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :guilabel:`Take` button on the system page no longer appears by default
for systems set to Automated, as this was a common source of confusion for
new users, and could result in users accidentally interrupting a running job.

The :guilabel:`Provision` tab on the system page now displays more details
regarding the current state of the provisioning mechanism, including whether
provisioning will occur directly or through the scheduler.

To temporarily give a user exclusive access to a system, loan it to them.
Once a loan is in place, the user with the loan will always have the ability
to :guilabel:`Take` the system, even if it is marked as Automated.

(Contributed by Dan Callaghan in :issue:`855333` and Nick Coghlan in
:issue:`1015131`)

.. versionchanged:: 0.15.1

   Beaker 0.15.0 included a more restrictive version of these changes.


Command line support for removing accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new subcommand :manpage:`bkr-remove-account(1)` has been added to the
Beaker command line client which allows Beaker admins to remove user
accounts.

For example, to remove the user accounts with usernames ``user1`` and
``user2``::

    bkr remove-account user1 user2

Removing an account disables Beaker access for that user, cancels any
currently incomplete jobs submitted, returns all system loans
and reservations, and transfers ownership of any systems to the
Beaker administrator running the account removal command.

(Contributed by Amit Saha in :issue:`966292`)


.. _enable-legacy-permissions-0.15:

Config option for legacy implicit job sharing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The implicit permission previously given to group co-members over jobs
is now enabled via an entry in Beaker's configuration file::

  beaker.deprecated_job_group_permissions.on = True

In the absence of the configuration entry, it defaults
to 'False'.

(Contributed by Raymond Mancy in :issue:`970501` and :issue:`1000861`)


Legacy "Lab Info" tab is hidden by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker currently includes some rudimentary asset management functionality,
a task that is better handled by a dedicated inventory management system
like `OpenDCIM <http://www.opendcim.org/>`__.

Starting with Beaker 0.15, the :guilabel:`Lab Info` tab in the system web UI is
hidden by default. While this tab will automatically be made visible if
the asset management fields already contain data, the overall feature is
considered deprecated and should not be used in new Beaker installations.

(Contributed by Dan Callaghan in :issue:`987313`)


Bug fixes and minor enhancements
--------------------------------

The initial Beaker 0.15 release was based on Beaker 0.14.1, and does not
include changes made in later Beaker 0.14.x maintenance releases.

A number of other smaller fixes and enhancements have been included in this
release.

* Recipe queue management updates

  * :issue:`954219`: The external watchdog will now correctly abort a recipe
    even if a system is stuck in an install loop due to Anaconda repeatedly
    rebooting the system after executing ``%pre``, but prior to starting
    execution of ``%post``
    (Contributed by Amit Saha)
  * :issue:`953543`: The external watchdog will now correctly abort a recipe
    even if a system is stuck in an install loop due to a kernel panic
    (Contributed by Raymond Mancy)
  * :issue:`977562`: Recipes will now be aborted if there are no candidate
    systems in Automated mode. Previously, affected recipes would remain
    queued indefinitely, even if all candidate systems were configured
    for Manual mode or marked as Broken. (Contributed by Raymond Mancy)

* System provisioning updates

  * :issue:`997629`/:issue:`994677`: Beaker now correctly forces all EFI
    systems to attempt netboot prior to local boot, even if the boot order
    is implicitly switched to prefer local boot during installation. This is
    needed to ensure the system can be automatically reprovisioned after
    use (Contributed by Raymond Mancy)
  * :issue:`1002261`: The ``btrfs`` technical preview can once again be
    selected as a partition filetype in Red Hat Enterprise Linux 6
    (Contributed by Nick Coghlan)
  * :issue:`968804` The provisioning system no longer caches netboot images
    on the lab controller, allowing it to handle in place updates that use
    the same image name (Contributed by Amit Saha)
  * :issue:`1006690`: Provisioning Fedora rawhide is now supported
    (Contributed by Amit Saha)
  * :issue:`997222`: The mechanism that attempts to automatically detect
    broken systems is now documented (Contributed by Dan Callaghan)


* Updates to server utilities

  * :issue:`994789`: The  ``beaker-sync-tasks`` task library update script
    once again works correctly and now has automated tests (Contributed by
    Amit Saha)
  * :issue:`957614`: ``beaker-expire-distros-via-qpid`` is now identified in
    activity logs as "QPID" rather than "XMLRPC" (Contributed by Raymond
    Mancy)
  * :issue:`999423`: The ``beaker-expire-distro-via-qpid`` command can once
    again be run as a foreground application (Contributed by Dan Callaghan)
  * :issue:`874386`: Importing the same distro tree simultaneously in two
    labs no longer triggers a database deadlock (this scenario was correctly
    resolved by the database, and was only likely to be encountered if two
    lab controllers were co-located and imported distro trees from the same
    file server (Contributed by Dan Callaghan)
  * :issue:`1002395`: The command used to generate yum repos is now
    configurable and Beaker uses ``createrepo_c`` by default. This is
    expected to reduce the impact task uploads have on the operation of
    the main server (Contributed by Raymond Mancy)

* Test harness updates

  * :issue:`1008433`: ``beah`` no longer depends on ``procmail`` (for its
    ``lockfile`` command) on distros that use ``systemd`` for service
    management (Contributed by Dan Callaghan)
  * :issue:`987332`: the support tasks needed in order to use Beaker's
    guest recipe functionality are now published in the beaker-project.org
    repositories (Contributed by Raymond Mancy)

* Other updates

  * :issue:`920018`: The system list no longer shows systems on disabled
    controllers (Contributed by Amit Saha)
  * :issue:`988848`: Searching for multiple CPU/Flags entries now gives the
    appropriate results (Contributed by Raymond Mancy)
  * :issue:`1001883`: Searching datetime fields with the ``is`` operator
    now gives the appropriate results (Contibuted by Dan Callaghan)
  * :issue:`999967`: The ``bkr job-list`` command once again works with the
    ``python-json`` package on Red Hat Enterprise Linux 5 (Contributed by
    Amit Saha)
  * :issue:`999733`: Individual recipe sets can now be cancelled over XML-RPC
    (Contributed by Nick Coghlan)
  * :issue:`989902`: The main Beaker server is now compatible with SQL
    Alchemy 0.8, in addition to 0.6 and 0.7 (Contributed by Dan Callaghan)
  * :issue:`759269`: An empty MOTD no longer causes spurious tracebacks in
    the server error log (Contributed by Dan Callaghan)
  * :issue:`993531`: spurious RPM %post output on new installations of
    beaker-server and beaker-lab-controller has been eliminated (Contributed
    by Dan Callaghan)
  * :issue:`965915`: The Beaker task library now has dedicated automated
    tests (Contributed by Raymond Mancy)
  * :issue:`998369`: The requirement for task RPM names to be unique is now
    enforced in the database (previously it was only checked on task
    upload) (Contributed by Amit Saha)
  * :issue:`990349`: The maximum group name length been increased to 255
    characters from 16 characters and is now properly validated by the
    XML-RPC API (Contributed by Amit Saha)
  * and :issue:`990821`: The maximum group display name length is now
    properly validated by the XML-RPC API (Contributed by Amit Saha)


Maintenance updates
-------------------

The following fixes have been included in Beaker 0.15 maintenance updates.


Beaker 0.15.1
~~~~~~~~~~~~~

Compatible changes from this release and the initial Beaker 0.15 release
were backported to create the Beaker 0.14.2 maintenance release.

* Restoring feature parity with Beaker 0.14:

  * :issue:`1015131`: Automated systems may once again be manually reserved,
    as long as a loan to a specific user is in place.
    (Contributed by Nick Coghlan)

  * :issue:`1015328`: This fills in some gaps in the 0.15 access migration
    rules.
    (Contributed by Dan Callaghan)

  * :issue:`1015081`: This makes the job matrix usable again. Also, some of the
    job matrix has been updated to use Bootstrap's default styling.
    (Contributed by Raymond Mancy)

  * :issue:`1014962`: Stops long task names from inhibiting the view of the
    task status.
    (Contributed by Dan Callaghan)

  * :issue:`1014875`: This fixes a deadlock introduced by conditional inserts.
    (Contributed by Raymond Mancy)

  * :issue:`1011858`: System loans are now handled in a consistent manner.
    (Contributed by Nick Coghlan)

* Logging

  * :issue:`1014868`: Anything that is logged by Beaker is now cleaned of
    NUL bytes, and replaced with the '\x00' literal.
    (Contributed by Dan Callaghan)

  * :issue:`1003709`: beaker-proxy was logging HTTP responses to stderr.
    They are now being logged via Beaker's regular logging handlers.
    (Contributed by Dan Callaghan)

* Job view

  * :issue:`7041601`: Recipe task result sub-tasks (or 'phases') no longer
    have a '/' or './' prepended to them.
    (Contributed by Dan Callaghan)

  * :issue:`1015017`: The :guilabel:`comment` link now works for failed
    recipes.
    (Contributed by Dan Callaghan)

  * :issue:`1014876`: Clicking the :guilabel:`Show Failed Results` button now
    displays all failures including fail/warn/panic.

* Beaker client

  * :issue:`1014623`: We now encode XML received on the client side in utf-8.
    This ensures non ascii characters are rendered properly, and encoding errors
    are avoided.
    (Contributed by Martin Kyral and Dan Callaghan)

  * :issue:`1009903`: Format the output of ``bkr list-labcontroller`` in a
    manner that is easier to read.
    (Contributed by Marian Ganisin)

* Other updates

  * :issue:`1013414`: When importing the latest RHEL7 distros, their addon
    repos will now be correctly added.
    (Contributed by Raymond Mancy)

  * :issue:`1009583`: The reserve workflow will now default to
    'None selected' in the :guilabel:`Tag` select field.
    (Contributed by Raymond Mancy)

  * :issue:`1017496`: Fixes a bug with typeaheads when Beaker is not mounted
    under '/'.
    (Contributed by Dan Callaghan)

  * :issue:`1014870`: Any HTML entered into the system notes are now escaped.
    (Contributed by Dan Callaghan)

  * :issue:`1014938`: The percentage bar should actually show the correct
    percentage now.
    (Contributed by Nick Coghlan)

  * :issue:`670438`: Stops the top menu from splitting when there is not enough
    horizontal space.
    (Contributed by Dan Callaghan)

  * :issue:`600232`: Long log file names are now truncated.
    (Contributed by Dan Callaghan)

  * :issue:`1008509`: ``beaker-provision`` will now kill a whole process group
    in order to avoid problems caused by a wayward child process.
    (Contributed by Raymond Mancy)


Beaker 0.15.2
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

In addition to the changes listed below, this release also includes all
changes from the Beaker 0.14.3 and 0.14.4 maintenance releases.

* Client updates

  * :issue:`1011378`, :issue:`1014899`: The new subcommand ``policy-list``
    provides command line access to the current access policy rules for a
    system.
    (Contributed by Amit Saha)
  * :issue:`734212`, :issue:`1039498`: The new subcommands ``loan-grant`` and
    ``loan-return`` provide command line access to grant and return system
    loans.
    (Contributed by Nick Coghlan)
  * :issue:`910750`: beaker-wizard now provides explicit support for
    creating Beakerlib libraries
    (Contributed by Iveta Senfeldova, Martin Kyral and Amit Saha)

* Updates to server utilities

  * :issue:`968847`: ``beaker-log-delete`` now supports basic-auth in addition
    to Kerberos authentication for remote log deletion. It has also been
    renamed from ``log-delete`` (although the latter name remains in place
    for backwards compatibility).
    (Contributed by Raymond Mancy)
  * :issue:`1012783`: beaker-sync-tasks now ensures the database and task repo
    remain consistent during task syncing, avoiding a race condition that
    could cause spurious recipe failures in the instance being updated.
    (Contributed by Raymond Mancy)

* Documentation updates

  * :issue:`968844`: The
    :ref:`Architecture Guide <architecture-archive-server>` and
    :ref:`Administration Guide <archive-server>` now cover how to configure
    an archive server.
    (Contributed by Raymond Mancy)

* Other updates

  * :issue:`1020091`: Group specific root passwords are now visible in the web
    UI for all members of that group, allowing secure sharing within Beaker,
    similar to the sharing of the system wide default password.
    (Contributed by Amit Saha)
  * :issue:`1039514`: A regression in Beaker 0.15.1 where viewing some
    systems anonymously could trigger an internal server error has been
    resolved.
    (Contributed by Nick Coghlan)
  * :issue:`1021425`: The search bar that was erroneously added to the OS
    versions page in Beaker 0.15 has once again been removed.
    (Contributed by Raymond Mancy)
  * :issue:`1021737`: Attempting to add a system with no data now reports an
    error rather than triggering an internal server error.
    (Contributed by Amit Saha)


Beaker 0.15.3
~~~~~~~~~~~~~

* Updates to related components

  * Version 0.7.0-1 of the Beah test harness has been released

    * :issue:`810893`: In addition to supporting testing on IPv4 only
      systems and dual IPv4/v6 systems with both stacks enabled, the ``beah``
      test harness now also supports testing on dual IPv4/v6 systems
      with the IPv4 support disabled. This feature currently has some
      `known limitations
      <http://beah.readthedocs.org/en/latest/admin.html#limitations>`__, but
      any IPv6 testing issues not already listed in that section of the
      ``beah`` documentation should now be reported as separate bugs against
      the Beaker ``test harness`` component (previously, all such reports
      would have been closed as duplicates of this RFE).
      (Contributed by Amit Saha)

    * :issue:`1054622`: beah no longer depends on python-simplejson when
      running on Fedora or Red Hat Enterprise Linux 6 or later.
      (Contributed by Amit Saha)

    * The ``beah`` harness now has its own documentation on
      `ReadTheDocs <http://beah.readthedocs.org>`__, in addition to the
      coverage of the task environment and development tools in the main
      Beaker documentation. (Contributed by Amit Saha)

  * The standard Beaker tasks have been moved to a dedicated
    `beaker-core-tasks
    <https://github.com/beaker-project/beaker-core-tasks>`__ git repo.

  * Maintenance of the ``/distribution/virt/install`` and
    ``/distribution/virt/start`` tasks has been moved to the upstream
    Beaker project.

  * Version 3.4-2 of the ``/distribution/reservesys`` task has been released.

    * :issue:`1055815`: ``/distribution/reservesys`` always sets a ``0``
      return code for improved interoperability with harnesses other than
      beah. (Contributed by Nick Coghlan)

  * Version 4.0-80 of the ``/distribution/virt/install`` task has been
    released.

    * :issue:`1048776`: Data in console logs on RHEL5 xen guests created by
      ``/distribution/virt/install`` is no longer duplicated.
      (Contributed by Jan Stancek)

  * Version 4.58-1 of the ``rhts`` test development and execution library has
    been released.

    * :issue:`1026670`: ``rhts-db-submit-result`` now retrieves full traces
      for dmesg failures delimited by lines containing ``[ cut here ]`` and
      ``end trace``. (Contributed by Amit Saha)
    * :issue:`1044913`: RPMs generated with ``make rpm`` or ``make bkradd``
      now include an additional "Provides:" entry that omits the git
      repository name. Setting the new ``RHTS_RPM_NAME`` variable allows
      the default name of the generated RPM to be overridden, with the
      default name still being included in the RPM as an additional
      ``Provides:`` entry. Setting the ``RHTS_PROVIDES_PACKAGE`` variable will
      also add an additional specific ``Provides:`` entry.
      These features together allow RHTS tasks to be moved to a new git
      repository without triggering :issue:`1040258` when new versions are
      uploaded following the relocation.
      (Contributed by Raymond Mancy and Nick Coghlan)

* System provisioning updates

  * :issue:`952661`: When a console log is available, the Beaker watchdog now
    monitors the Anaconda installation process for failures and aborts the
    recipe immediately (reporting the relevant details), rather than waiting
    for the external watchdog to time out. The monitoring details can be
    :ref:`configured by the Beaker administrators <customizing-panic>` and
    opting out of panic monitoring for a recipe also opts out of installation
    failure monitoring (a future release of Beaker will allow these two
    settings to be configured independently). (Contributed by Dan Callaghan)

  * :issue:`915272`: The new ``autopart_type`` ks_meta option allows the
    selection of specific automatic partitioning schemes in recent versions
    of Anaconda. (Contributed by Amit Saha)

  * :issue:`1055753`: ``/etc/rc.d/init.d/anamon`` and
    ``/usr/local/sbin/anamon`` now have the correct SELinux context on
    Red Hat Enterprise Linux 7.
    (Contributed by Dan Callaghan)

  * :issue:`1054616`: Power configurations without a password set are now
    handled correctly. (Contributed by Raymond Mancy)

* System management updates

  * :issue:`986177`: The new ``beaker-create-kickstart`` command-line tool
    allows Beaker administrators to create and debug new kickstart templates
    and snippets without needing to reprovision systems.
    (Contributed by Raymond Mancy)

  * :issue:`987157`: System records exported from Beaker as CSV files now
    include the system ID, allowing the systems to be assigned a new FQDN
    by changing the FQDN column and reimporting the file.
    (Contributed by Amit Saha)

  * :issue:`1037592`: The new ``bkr system-status`` command provides command
    line access to the details of the current machine user, loan recipient
    and running recipe (if any), as well as its current condition (Automated,
    Manual, Broken, Removed). (Contributed by Raymond Mancy)

* Other updates

  * :issue:`1052043`: The CSS for the system page has been adjusted to
    improve readability. (Contributed by Dan Callaghan)
  * :issue:`1040226`: ``beaker-sync-tasks`` no longer logs in when it doesn't
    need to. (Contributed by Amit Saha)
  * :issue:`1022776`: The 'Job Design' section of the docs now correctly
    describes the availability and impact of the legacy permissions setting.
    (Contributed by Raymond Mancy)
  * :issue:`1043787`: The whiteboard select field on the Job Matrix Report
    page is now wider to improve readability. (Contributed by Dan Callaghan)
  * :issue:`975486`: ``beaker-watchdog`` will now detect a panic even when it
    crosses block boundaries. (Contributed by Dan Callaghan)
  * :issue:`1040299`: Changes to a group’s root password via the webUI are now
    visible in the activity page. (Contributed by Amit Saha)
  * :issue:`1011400`: Running 'bkr policy-grant' for an invalid group or user
    now gives an appropriate error message. (Contributed by Amit Saha)
  * :issue:`978661`: 'Root Password Expiry' is now consistently displayed on
    the preferences page.
  * :issue:`1043390`: User typeaheads now work on the user page.
    (Contributed by Dan Callaghan)
  * :issue:`979277`: The formatting requirements for Beaker CSV imports are
    now documented and linked from the main web interface.
    (Contributed by Amit Saha)
  * :issue:`1019537`: Lab controller daemons now log details of unhandled
    XML-RPC exceptions. (Contributed by Dan Callaghan)
  * :issue:`1054035`: Unicode box drawing characters are no longer mangled
    in the console log. (Contributed by Dan Callaghan)
  * :issue:`856279`: an appropriate error message is now logged when the
    ``beaker-transfer`` daemon encounters an rsync failure.
    (Contributed by Dan Callaghan)
  * :issue:`650758`: The search field previously labelled as "Distro" in the
    task detail page is now correctly labelled as "OSMajor".
    (Contributed by Dan Callaghan)
  * :issue:`1022333`: A previously specified product association may now be
    removed from a recipe set. (Contributed by Dan Callaghan)
  * :issue:`877344`: ``bkr job-modify`` can now remove the product association
    from a recipe set. (Contributed by Dan Callaghan)
  * :issue:`1037878`: Importing a system via CSV now fully validates the
    imported data. (Contributed by Amit Saha)
  * :issue:`1021738`: Server can no longer ever report None for a system FQDN.
    (Contributed by Amit Saha)
  * :issue:`1034271`: ``beaker-client`` no longer depends on
    ``python-simplejson`` on platforms with a sufficiently recent version
    of Python. (Contributed by Dan Callaghan)


Beaker 0.15.4
~~~~~~~~~~~~~

* Updates to related components

  * Version 0.7.2-1 of the Beah test harness has been released

    * :issue:`1062896`: the harness once again works when ipv6 is not
      available. (Contributed by Amit Saha)

    * :issue:`1059479`: the harness can now retrieve and execute additional
      tasks after IPv6 has been disabled. (Contributed by Dan Callaghan)

    * :issue:`1063815`: the RHTS_PORT parameter is now correctly converted
      to an integer prior to use. (Contributed by Marian Csontos)

  * Version 3.4-3 of the ``/distribution/reservesys`` task has been released.

    * :issue:`746003`: ``/distribution/reservesys`` now correctly preserves
      the  SELinux context of ``/etc/motd``. (Contributed by Dan Callaghan)

  * Version 1.12-1 of the ``/distribution/install`` task has been released.

    * :issue:`893078`: ``/distribution/install`` no longer creates an
      irrelevant ``/etc/syslog.conf`` file on RHEL6 and later releases
      (Contributed by Dan Callaghan)

  * Version 4.59-1 of the ``rhts`` test development and execution library has
    been released.

    * :issue:`1060900`: The ``arm``, ``armhfp`` and ``aarch64`` ARM variants
      are now accepted as valid architectures for tasks.
      (Contributed by Amit Saha)

* System provisioning updates

  * :issue:`1063090`: The new ``beah_rpm`` ks_meta variable allows users to
    select a particular available ``beah`` version for a recipe (for example,
    ``beah_rpm=beah-0.6.48`` to select the last IPv4-only version of the
    harness). (Contributed by Dan Callaghan)

  * :issue:`1057148`: Beaker's Anaconda installation monitoring now captures
    all files that match the pattern ``/tmp/anaconda-tb*``.
    (Contributed by Amit Saha)

* System management updates

  * :issue:`1063893`: The ``edit_policy`` permission now includes the ability
    to change the system owner, restoring functional parity with the system
    ``admin`` group feature used in Beaker 0.14 and earlier releases.
    (Contributed by Nick Coghlan)

* Other updates:

  * :issue:`1063313`: The size of the combo box used to select a product for
    log retention purposes has been adjusted to handle browsers that don't
    automatically resize the dropdown to fit the values.
    (Contributed by Dan Callaghan)

  * :issue:`886816`: Queries for ``<hypervisor/>`` with  ``op="!="`` in
    ``<hostRequires/>`` now correctly include bare metal systems.
    (Contributed by Dan Callaghan)

  * :issue:`1058549`: CSV key value import is now consistent with other
    system CSV import operations and implicitly creates new systems as
    needed. (Contributed by Amit Saha)

  * :issue:`1062529`: The ``--update`` option is once again passed to the
    repo metadata creation command when updating the task library.
    (Contributed by Dan Callaghan)

  * :issue:`1059079`: Lab controller daemons now ensure they always create a
    new connection after an XML-RPC failure. (Contributed by Nick Coghlan)

  * :issue:`1040794`: The  "Oops" entry in the default setting for PANIC_REGEX
    has been adjusted to "Oops: " after a user encountered the "Oops" sequence
    in a randomly generated temporary filename. (Contributed by Dan Callaghan)

  * :issue:`1062480`: Queries in the main scheduler now use a more efficient
    mechanism to exclude previously deleted recipes from consideration.
    (Contributed by Raymond Mancy)

  * :issue:`1022888`: ``bkr watchdog-show`` for a currently "waiting" task
    now shows "N/A" for the remaining duration rather than failing.
    (Contributed by Raymond Mancy)

.. Skip reporting (appeases the draft release note generator):

  * :issue:`1046194` (relates to an RH specific component)
  * :issue:`1061977` (relates to an RH specific component)
  * :issue:`1061976` (relates to an RH specific component)

Beaker 0.15.5
~~~~~~~~~~~~~

* Version 0.7.3 of the Beah test harness has been released, with one bug fix: 

  * :issue:`1067745`: The ``beah-beaker-backend`` service now listens on all
    network interfaces, not just loopback. This fixes a regression introduced 
    in Beah 0.7.2 where multi-host testing did not work because the other Beah 
    processes in the recipe set were not reachable over the network. 
    (Contributed by Dan Callaghan)

* Other updates:

  * :issue:`1066586`: Users who have reserve permission on a Secret/NDA
    system are now allowed to see the system. This matches the behaviour of 
    group systems in Beaker 0.14 and earlier. (Contributed by Dan Callaghan)

  * The :program:`beaker-repo-update` command appends a trailing slash to the
    harness base URL if it is missing. (Contributed by Dan Callaghan)
