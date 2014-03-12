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
      <fetch url="git://git.beaker-project.org/beaker-core-tasks#master"
             subdir="reservesys" />
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
one enhancement: the MOTD and notification e-mail now refer to the Beaker user 
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
