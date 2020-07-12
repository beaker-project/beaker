What's New in Beaker 0.16?
==========================

The principal feature added in Beaker 0.16 is experimental server-side support 
for "external tasks".


External tasks
--------------

In this release, recipe tasks have been de-coupled from the task library. It is 
now possible to specify tasks in a recipe using an external URL without any 
corresponding task in Beaker's task library.

Note that this feature requires support on the harness side for fetching and 
unpacking tasks from arbitrary URLs. This release only covers the server 
support necessary for external tasks. At this time, Beah has not been updated 
to support external tasks.

When a recipe refers to a task in the task library by name, the XML exposed to 
the harness includes an ``<rpm/>`` element describing the RPM from the task 
library. This behaviour remains unchanged from previous releases.

::

    <task name="/distribution/reservesys">
      <rpm name="beaker-core-tasks-distribution-reservesys"
           path="/mnt/tests/distribution/reservesys" />
      ...
    </task>

The server now also accepts tasks containing a ``<fetch/>`` element, which 
describes an external location for the task's source code. In this case the 
task need not exist in Beaker's task library. The ``<fetch/>`` element is 
included in the XML exposed to the harness, so that it can fetch and unpack the 
task before running it.

::

    <task name="/distribution/reservesys">
      <fetch url="https://github.com/beaker-project/beaker-core-tasks/archive/master.tgz#reservesys"/>
      ...
    </task>

Each recipe task now tracks its name and version independently of the task 
library. For external tasks, the harness can populate the name and version in 
the recipe results (see :http:patch:`/recipes/(recipe_id)/tasks/(task_id)/`). 
For tasks from the task library, the scheduler populates the version at the 
start of the recipe.

Refer to the :ref:`beakerdev:proposal-external-tasks` design proposal for more 
background information.

(Contributed by Bill Peck and Dan Callaghan in :issue:`1057459`, 
:issue:`576304`)


Configurable quiescent period for system power
----------------------------------------------

Each system now has a configurable "quiescent period", measured in seconds. 
Beaker will ensure that consecutive power commands for a system are delayed by 
this amount of time. This feature can be used when a system's power supply 
cannot tolerate rapid cycling.

System owners can set the quiescent period on the :guilabel:`Power Config` tab 
of the system page. The default is 5 seconds, which matches the hardcoded delay 
during reboot commands in previous Beaker versions.

(Contributed by Raymond Mancy in :issue:`867761`)


"View" permission in system access policies
-------------------------------------------

System access policies have a new permission, "view", which controls who can 
see the system in Beaker's inventory. This replaces the previous "Secret" flag 
for systems, giving finer grained control over visibility. The default for new 
systems is to grant "view" permission to everybody.

(Contributed by Dan Callaghan)


Password hashes use a more secure, salted form
----------------------------------------------

Beaker account passwords are now stored in a more secure form, using PBKDF2 
with SHA512 HMAC and a unique random salt per user. The password storage 
implementation is provided by the `passlib <http://pythonhosted.org/passlib/>`_ 
library. Existing password hashes will be automatically upgraded to the new 
format when the user next logs in.

Previously Beaker stored an unsalted SHA1 hash of each password. The 
documentation advised against using password authentication in production 
environments because of the potential for passwords to be cracked if the 
password hashes were leaked. With this enhancement, Beaker's password 
authentication is now considered suitable for production use.

(Contributed by Dan Callaghan in :issue:`994751`)


Task updates
------------

Version 3.4-4 of the ``/distribution/reservesys`` task has been released, with 
one enhancement: the MOTD and notification email now refer to the Beaker user 
preferences page for the system root password, as a hint to new users. 
(Contributed by Dan Callaghan in :issue:`950640`)

The ``/distribution/utils/dummy`` task is now published on the Beaker web site. 
This is a trivial task which does nothing and passes immediately. It can be 
used in multi-host testing, to align tasks in different recipes across the 
recipe set. (:issue:`1054651`)


Bug fixes and minor enhancements
--------------------------------

A number of other smaller fixes and enhancements to Beaker are included in this 
release.

* :issue:`1012389`: Beaker administrators can now update the name and expiry
  time for existing retention tags. (Contributed by Dan Callaghan)
* :issue:`958357`: The scheduler now emits a Graphite counter
  ``beaker.counters.recipes_submitted`` for the number of recipes submitted. 
  (Contributed by Dan Callaghan)
* :issue:`1044934`: The Beaker server now avoids leaving stale yum metadata in
  the task library when a task is downgraded. (Contributed by Amit Saha)
* :issue:`874191`: A new kickstart metadata variable ``no_updates`` disables
  the Updates repo during Fedora installations. (Contributed by Dan Callaghan)
* :issue:`1067924`: Beaker no longer adds quotes to kernel options containing
  shell metacharacters. (Contributed by Dan Callaghan)
* :issue:`1066122`: Tasks which have not started yet no longer occupy extra
  vertical space for no reason in the recipe results display. (Contributed by 
  Nick Coghlan)
* :issue:`1062469`: The ``command_queue.status`` database column is now
  indexed, which improves the performance of the command queue polling loop.
  (Contributed by Dan Callaghan)
* The SQL queries which :program:`beakerd` uses to produce recipe queue metrics
  are now more efficient and will place less load on the database server. 
  (Contributed by Raymond Mancy)
* :issue:`1027516`: The :program:`beaker-repo-update` command no longer runs
  ``createrepo`` if the harness packages have not changed, making its operation 
  substantially faster in some circumstances. (Contributed by Dan Callaghan)
* :issue:`999056`: When cloning a job, tasks with no parameters no longer
  include a superfluous ``<params/>`` element in the cloned XML. (Contributed 
  by Dan Callaghan)
* :issue:`1072133`: The watchdog time remaining is now displayed correctly on
  the recipe page for values larger than 10 hours. (Contributed by Dan 
  Callaghan)
* :issue:`1067243`: If the authentication settings for the lab controller
  daemons are incorrect, the daemons will now report an error when they are 
  started, instead of starting and then failing to work properly. (Contributed 
  by Dan Callaghan)
* :issue:`1071389`: Fixed a regression in the lab controller daemons' handling
  of network failures during XML-RPC requests on Python 2.6. (Contributed by 
  Dan Callaghan)
* :issue:`580118`: The :program:`bkr` client now prints an error message
  instead of an uncaught exception when the user's Kerberos ticket has expired. 
  (Contributed by Dan Callaghan)
* :issue:`1058152`, :issue:`1058156`: Argument handling and error reporting
  for the :program:`beaker-create-kickstart` server command has been improved 
  to handle more corner cases. (Contributed by Raymond Mancy)
* :issue:`1028302`: The virtualization workflow documentation referred to an
  example job XML definition, but the XML was missing. This has now been filled 
  in. (Contributed by Amit Saha)
* :issue:`994644`: The documentation about adding systems to Beaker has been
  expanded to cover install options, including some recommendations for setting 
  ``ksdevice`` on systems which have EFI firmware and multiple NICs. 
  (Contributed by Dan Callaghan)
* Long options are now displayed correctly (using two hyphens rather than an
  en-dash) in the HTML version of the Beaker man pages. (Contributed by Raymond 
  Mancy)

Version 4.60 of the ``rhts`` test development and execution library has also 
been released, with the following fixes:

* :issue:`1072299`: The AVC checking logic in ``rhts-test-env`` now supports
  suppressing AVC checks for an individual result within a task. (Contributed 
  by Jan Stancek)
* :issue:`1066714`: The ``rhts-devel`` script for building task RPMs no longer
  leaks temporary build directories in :file:`/mnt/testarea`. (Contributed by 
  Amit Saha)

.. Not reporting these unreleased regressions:

   * :issue:`1070561`: Meet ISE 500 if power address is blank
   * :issue:`1072127`: attempting to use bkr client password authentication on an account with no password causes XML-RPC fault: TypeError: hash must be unicode or bytes, not None
   * :issue:`1074345`: initial watchdog value at start of task is 60*60*24 times too long


Maintenance updates
-------------------

The following fixes have been included in Beaker 0.16 maintenance updates.

Beaker 0.16.1
~~~~~~~~~~~~~

* :issue:`1078941`: Fixed a regression which caused the ``distros.get_arch``
  XML-RPC method to fail. This method is called by workflow commands when 
  specifying a distro family and no architectures. (Contributed by Dan 
  Callaghan)
* :issue:`1080685`: Fixed a regression where the :guilabel:`Release Action`
  field in the system power configuration was always saved as "Power Off" 
  regardless of the selected value. (Contributed by Dan Callaghan)
* :issue:`1079816`: The power quiescent period is now obeyed for consecutive
  power commands. (Contributed by Dan Callaghan)
* :issue:`1079603`: Reboot commands are now implemented as separate 'off' and
  'on' commands, so that the quiescent period takes effect between them. 
  (Contributed by Dan Callaghan)
* :issue:`1078620`: The :doc:`database upgrade instructions for Beaker 0.16
  <upgrade-0.16>` have been updated to correctly set the quiescent period for 
  existing rows. (Contributed by Dan Callaghan)
* :issue:`1026730`: The :program:`bkr` client includes a :ref:`new workflow
  command <bkr-workflow-installer-test>` which can be used to test Anaconda 
  behaviour. The command generates a kickstart and kernel options on the client 
  side using a Jinja template. (Contributed by Alexander Todorov)
* :issue:`1076322`: The entry fields for user and group in the system access
  policy editor have been made more robust. An explicit action is now required 
  to add a new row (click :guilabel:`Add` or press Enter) instead of adding 
  a row implicitly when the field is blurred. Typeahead suggestions now appear 
  for new groups which were created after the typeahead cache was prefetched. 
  (Contributed by Dan Callaghan)
* :issue:`883887`: If the same package is specified multiple times in
  a recipe's ``<packages/>``, the duplicates are now ignored instead of causing 
  a database error. (Contributed by Matt Jia)
* :issue:`1005865`: Beaker no longer requires a local harness repo to be
  present if the recipe is using an alternative harness. (Contributed by Amit 
  Saha)
* :issue:`1074832`: The :program:`bkr` client now prints an error message
  instead of an uncaught exception when the Kerberos credential cache does not 
  exist. (Contributed by Dan Callaghan)

Beaker 0.16.2
~~~~~~~~~~~~~

* :issue:`1065811`: A new :ref:`kickstart metadata <kickstart-metadata>`
  variable ``beah_no_ipv6`` will cause Beah to avoid using IPv6 even when it is 
  available. You should set this variable in your recipe if it performs 
  destructive network testing which affects IPv6 connectivity. (Contributed by 
  Amit Saha)
* :issue:`1083562`: Lab controllers which have been removed are no longer
  included in the output of :program:`bkr list-labcontrollers`. (Contributed by 
  Raymond Mancy)
* :issue:`1085047`: The "secret" column no longer appears in the system CSV
  export. The column contained no values and would cause an error when the CSV 
  was imported. (Contributed by Amit Saha)
* :issue:`1085149`: Updates to the ``system_status_duration`` table are no
  longer leaked to the database if any errors occur during CSV import. 
  (Contributed by Dan Callaghan)
* :issue:`1085238`: Beaker now displays an error message when importing a CSV
  file which contains no rows. (Contributed by Amit Saha)
* :issue:`999391`: The :guilabel:`Loan Settings` widget on the system page now
  displays descriptive error messages from the server rather than just 
  indicating that the request failed. (Contributed by Matt Jia)
* :issue:`952635`: Package names containing colons are now correctly passed
  through to the ``%packages`` section of the kickstart. (Contributed by Dan 
  Callaghan)
* :issue:`1073767`: Groups names in the system access policy view are now
  hyperlinks to the respective group page. (Contributed by Matt Jia)
* :issue:`1078610`: The output of :program:`bkr workflow-installer-test` is now
  consistent with other workflow commands. (Contributed by Amit Saha)
* :issue:`966339`: The :program:`beaker-init` tool now makes the admin user an
  owner of the admin group on fresh Beaker installations. (Contributed by Dan 
  Callaghan)
* :issue:`1077555`: The vim modeline in tasks generated by
  :program:`beaker-wizard` now uses ``dict+=`` instead of ``dict=`` to avoid 
  interfering with the user's custom spelling dictionary. (Contributed by 
  Branislav Blaškovič)

The following related components were also updated with this release:

* Version 0.7.4-1 of the Beah test harness has been released.

  * :issue:`1065811`: A new config option ``IPV6_DISABLED`` will cause Beah
    to avoid using IPv6 even when it is available. This can be set from 
    a Beaker recipe by passing ``beah_no_ipv6`` as a kickstart metadata 
    variable. (Contributed by Amit Saha)
  * :issue:`1072284`: Beah now starts after systemd readahead collection is
    finished. (Contributed by Amit Saha)

* Version 4.61-1 of the ``rhts`` test development and execution library has
  been released.

  * :issue:`1069112`: Task RPMs now always have ``rwxr-xr-x`` as the
    permissions for directories. This avoids RPM conflicts if the task was 
    built on a system where the rpmbuild directory inherits a different mode, 
    for example due to file system ACLs. (Contributed by Dan Callaghan)

* Version 3.4-5 of the ``/distribution/reservesys`` task has been released.

  * :issue:`1077092`: Removed requirement on ``unifdef`` since it was not
    needed for anything and is no longer available in recent distros. 
    (Contributed by Dan Callaghan)

.. unreleased regressions:
   * :issue:`1085028`: group name links in access policy tab do not URL-encode group names
