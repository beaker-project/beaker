What's New in Beaker 0.15?
==========================

The principle feature added in Beaker 0.15 is
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

(Contributed by Dan Callaghan and Nick Coghlan)

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


Updates to supported queries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SQL filtering criteria to determine if a system is available for use
by all users of a given Beaker instance has changed from "the system is
marked as shared and is not in any system groups" to "the system
access policy grants the 'reserve' permission to all users of the instance".

This `update to an affected supported query
<http://git.beaker-project.org/cgit/beaker/commit/Server/bkr/server/reporting-queries/machine-hours-by-user-arch.sql?id=d490c01c77ae0b1e269a6f44f411f92f4f87c787>`__
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

* Restoring feature parity with Beaker 0.14:

  * :issue:`1015131`: Automated systems may once again be manually reserved,
    as long as a loan to a specific user is in place.
