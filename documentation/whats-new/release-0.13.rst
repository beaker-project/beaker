What's New in Beaker 0.13?
==========================

The principal feature added in Beaker 0.13 is the initial implementation of
elements of the :ref:`proposal-enhanced-user-groups` design proposal.

Migrating to Beaker 0.13
------------------------

There are no changes in this release that should impact task or job
compatibility.

The new :ref:`group-jobs-0.13` feature is intended to completely replace
the existing behaviour where group members are automatically granted
increased access to all jobs submitted by fellow group members. Accordingly,
the legacy implicit sharing behaviour is now deprecated and will be removed
in the next Beaker release. This phased removal should allow users to
switch to using explicitly shared group jobs before the implicit sharing is
removed.

.. note::

   This interim backwards compatibility with the old system *does* create a
   loophole where it is possible to create a new group, add another user to
   it and then have additional access to their jobs. The current release will
   track any such behaviour in the group and job activity logs, until the
   removal of the old implicit job sharing model in the next release prevents
   it entirely.


.. _group-jobs-0.13:

Group jobs
----------

Beaker 0.13 allows job submitters to specify a group owner for a job. This
is done via the ``group`` attribute on a job XML's ``<job>`` element, or by
passing the ``--job-group`` option to a client workflow command. All members
of the associated group will have the same permissions to view and modify
a job as the original submitter.

In addition, the public SSH keys for all group members will be added to any
systems provisioned for a group job, and group owners may optionally set a
shared root password for the group that will be used on those systems.

The owning group (if any) for each job is given on the job details page, as
well as in the global and individual job lists. The field is also made
available as a new option when filtering the job lists.

The list in "My Jobs" has been updated to include both jobs submitted by the
user and those that have been submitted on behalf of any groups they belong
to. The new filtering options can be used to limit the list back to just
those jobs the user has submitted directly.

(Contributed by Raymond Mancy, Amit Saha and Dan Callaghan, primarily in
:issue:`908183`, :issue:`908186`, :issue:`952980`, :issue:`961192`,
:issue:`961194`, and :issue:`961580`.)


More flexible user groups
-------------------------

Historically, creating and populating user groups in Beaker has been limited
to the administrators of a Beaker instance. With the introduction of the
group jobs feature, it is desirable that users have more direct control over
the groups defined in Beaker.


Creating user groups
~~~~~~~~~~~~~~~~~~~~

Beaker users can now create user groups without admin privileges. A new
sub-command ``bkr group-create`` is added to create a group from
the command line. New groups can also be defined through the
Groups and My Groups pages in the web UI.

(Contributed by Amit Saha in :issue:`908172`.)


Modifying user groups
~~~~~~~~~~~~~~~~~~~~~

Beaker users can modify group details (group name, display name) and
change the group membership (add/remove group members) of the groups
they own. Users will get an email notification when their membership
changes (added/removed).

Existing group owners can also grant and revoke ownership privileges,
allowing a group to have multiple co-owners.

A new sub-command ``bkr group-modify`` has been added to
modify the group details from the command line. Groups details
can also be accessed and updated through the Groups and My Groups pages
in the web UI.

(Contributed by Amit Saha and Dan Callaghan, primarily in :issue:`908174`,
:issue:`908176`, :issue:`952978`, :issue:`961248` and :issue:`970493`.)


LDAP groups
~~~~~~~~~~~

In addition to allowing all users to create new groups, Beaker 0.13 allows
Beaker admins to define new groups that are automatically populated from
an external LDAP directory.

These groups are automatically refreshed daily from LDAP, but admins can also
force an immediate update by running ``beaker-refresh-ldap`` on the main
Beaker server.

(Contributed by Dan Callaghan in :issue:`908173`.)


Notable enhancements
--------------------


Improved documentation for task development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new section on :ref:`writing-tasks` in the Beaker documentation covers how
to create new tasks, details of the metadata that can be defined for tasks,
details of the environment variables automatically defined by Beaker when
running a task, and the command line tools that are automatically provided
for use by tasks during execution.

The standard tasks provided along with Beaker have also been documented.

The task related documentation has also been updated to ensure it is accurate
for current versions of Beaker.

(Contributed by Dan Callaghan, Amit Saha and Nick Coghlan in :issue:`872421`,
:issue:`921346`, and :issue:`960317`.)


Command line tool for listing group members
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new beaker command, ``bkr group-members`` is now available for
listing a group's members. This command returns the username, email
for each member and also identifies whether the member is a group
owner or not.

(Contributed by Amit Saha.)


Chrony is enabled when appropriate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``chrony`` clock synchronization daemon is now installed and enabled by
default for recipes running on supported versions of Fedora and other
related distros where the ``ntpd`` daemon is no longer available. In
addition, the harness is now configured to  wait for clock synchronization
before it starts.

If you want to opt out of this behaviour (for example, if the presence of the 
chrony package interferes with your testing) you can pass 
``ks_meta="no_clock_sync"`` in your job XML.

(Contributed by Bill Peck and Dan Callaghan in :issue:`901670`.)


Power script for Hyper-V guests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new power script was added for controlling Hyper-V guests. This allows you to 
add predefined Hyper-V guests as systems in Beaker, similar to the existing 
``virsh`` power script.

(Contributed by Ladislav Jozsa in :issue:`884558`.)


``optional-debuginfo`` repos are imported
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``beaker-distro-import`` now correctly imports the ``optional-debuginfo``
repository (where it is available). To add this repo to already imported
distros, the distros will have to be re-imported.

(Contributed by Raymond Mancy in :issue:`952963`.)


System filtering using inventory date and status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new XML element ``<last_inventoried>`` has been added to enable
system filtering using the date on which the system was last
inventoried. For example, to specify that your job should be run on a
system inventoried after 2013-01-02, you should add the following in
your job XML::

    <hostRequires>
        <system> <last_inventoried op="&gt;" value="2013-01-02" /> </system>
    </hostRequires>

Besides the above utility, this enhancement also allows you to use the
``bkr`` command line tool to list systems based on their last
inventoried status or date using the ``--xml-filter`` option.

(Contributed by Amit Saha in :issue:`949777`.)


System search using inventory date and status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is now possible to search for systems from the Beaker Web UI (See
:ref:`system-searching`) based on the date when they were last
inventoried.

This can also be used to check the inventory status of the
systems. Searching for systems using the "is" operator with a blank
date value returns all uninventoried systems, where as using the "is
not" operator will return all inventoried systems.

(Contributed by Amit Saha in :issue:`949777`.)


Bug fixes and minor enhancements
--------------------------------

A number of other smaller fixes and enhancements have been included in this
release.


Client tools
~~~~~~~~~~~~

* :issue:`929202`: ``beaker-wizard`` package detection is once again supported
* :issue:`929190`: ``beaker-wizard`` is now compatible with more recent
  versions of the ``python-bugzilla`` support library.
* :issue:`952486`: ``rhts-test-env`` no longer depends on ``beakerlib``
  (when appropriate, Beaker now installs ``beakerlib`` explicitly on
  provisioned systems).


Provisioning and task execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* :issue:`886875`: Kernel options of the form ``key=value1 key=value2``
  are once more correctly added to a recipe instead of being passed
  through as ``key=value2``.
* :issue:`929116`: Non-ASCII characters are now supported in job and recipe
  whiteboards.
* :issue:`903416`: The handling of kickstarts for Red Hat Storage has been
  updated so that the variable RHS specific elements are retrieved
  automatically from the distro tree.


Alternative harnesses
~~~~~~~~~~~~~~~~~~~~~

* :issue:`961300`: Uploading an empty log file is now permitted.
* :issue:`962253`: Uploading a log file to a finished task now returns a
  409 Conflict response instead of triggering an internal server error.
* :issue:`962254`: Reporting a result for a finished task now returns a
  409 Conflict response instead of triggering an internal server error.
* A specific 411 Length Required response is now returned for a missing
  ``Content-Length`` header when uploading a log file, rather than a
  general 400 Bad Request.

Miscellaneous changes
~~~~~~~~~~~~~~~~~~~~~

* :issue:`970512`: Systems can once again be removed from a group directly
  from the group's page
* :issue:`955868`: XML filtering based on a system's Added data now gives
  sensible results.
* :issue:`963700`: The URL scheme, hostname and port used to serve uploaded
  log files are now configurable.
* :issue:`962582`: All Beaker components now require version 1.0 or later
  of the ``python-requests`` library.
* :issue:`957577`: ``bkr`` is now a properly stateless Python namespace
  package.
* :issue:`951985`: ``beaker-import`` now handles failing to import a
  distro tree with a ``%`` character in the error message
* :issue:`903902`: Eliminated a race condition when marking systems broken.
* :issue:`952929`: Eliminated a race condition in the application log
  initialisation.
* :issue:`962901`: Eliminated a race condition when archiving console logs.
* :issue:`880855`: Eliminated a race condition when creating per-recipe
  repositories.
* :issue:`950895`: Mitigated the negative effects of interference between
  processing of queued recipes and completion of recipes.


Maintenance updates
-------------------

The following fixes have been included in Beaker 0.13 maintenance updates.


Beaker 0.13.1
~~~~~~~~~~~~~

Bug fixes:

* :issue:`974382`: Distro trees for Red Hat Enterprise Linux 4 can once again
  be imported into Beaker.


Beaker 0.13.2
~~~~~~~~~~~~~

Minor features:

* :issue:`973092`: Setting "grubport=" in the kickstart metadata is now
  supported
* :issue:`973595`: btrfs volumes can now be created when installing with
  recent anaconda versions
* :issue:`973893`: The Administrator's Guide now covers how to upgrade an
  existing Beaker installation to a new maintenance or feature release
* :issue:`972417`: Beaker workflow commands now default the number of clients
  and servers to zero, allowing the options to be used independently

Bug fixes:

* :issue:`952587`: Some steps in the job scheduler have been serialised
  to eliminate scheduling anomalies seen with the previous approach.
* :issue:`974352`: XML-RPC retries on lab controllers are now logged correctly
* :issue:`974319`: Lab controller requests left over from a previous network
  failure are now purged without aborting new recipes running on affected
  systems
* :issue:`972397`: Sorting certain combinations of data grid columns no
  longer triggers an internal server error
* :issue:`972411`: Submitting malformed CSV to CSV import no longer
  triggers an internal server error
* :issue:`972412`: Submitting invalid UTF-8 characters in job XML no
  longer triggers an internal server error
* :issue:`957011`: RHEL 6 Kickstarts are once again generated correctly when
  provisioning systems in manual mode
* :issue:`979999`: The link to the Relax NG schema from the docs home page
  has been fixed.
