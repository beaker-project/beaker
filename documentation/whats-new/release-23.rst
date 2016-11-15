What's New in Beaker 23?
========================

Beaker 23 provides a new recipe state to reflect the provisioning of a machine,
generates GRUB2 menus for x86 EFI systems, an improved user experience for job
and recipe pages, as well as many other improvements.

Notable changes
---------------

New status reflecting the provisioning of the machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In previous Beaker versions, determining whether the installation had finished
and tasks had started was hard to figure out. Furthermore, no timestamp was
visible in the UI to see when the installation of the system had actually
started.

For Beaker 23, a new status ``Installing`` has been added to reflect the
provisioning of the machine. The timestamp of the start and end of the
installation is visible in a designated tab of the recipe page.

(Contributed by Dan Callaghan in :issue:`991245`.)

Limits on number of results and result logs per recipe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker now enforces an upper limit on the total number of results and result 
logs in a single recipe. By default the limits are 7500 results and 7500 result 
logs, but the Beaker administrator can adjust or disable the limits.

The limits are intended as an extreme upper bound which should not interfere 
with normal testing, but will prevent a runaway task from accidentally 
producing so many results that it can cause problems elsewhere in Beaker (for 
example, very large recipes cause excessive memory usage in 
:program:`beaker-transfer`, :program:`beaker-log-delete`, and when rendering 
results in the web UI).

(Contributed by Dan Callaghan in :issue:`1293007`.)

Job results email links to recipes
----------------------------------

Within job notification emails, Beaker now provides a URL to display associated
failed recipe results. Beaker previously included ``OSVersion:`` for each
recipe, for example::

    RecipeID: 14304 Arch: x86_64 System: dev-kvm-guest-10.example.com Distro: RHEL-6.7-20150702.0 OSVersion: RedHatEnterpriseLinux6.7 Status: Completed Result: Fail

In this release the ``OSVersion:`` field has been removed
to save horizontal space, since it is redundant with the
``Distro:`` field. The URL for the recipe now appears
at the end of the line, for example::

    RecipeID: 14304 Arch: x86_64 System: dev-kvm-guest-10.example.com Distro: RHEL-6.7-20150702.0 Status: Completed Result: Fail <https://beaker-devel.app.eng.bos.redhat.com/recipes/14304>

(Contributed by Blake McIvor in :issue:`1326968`.)

Improved user interface for jobs and recipes
---------------------------------------------

This release provides an overhauled web UI for job and recipe pages.
(Contributed by Matt Jia and Dan Callaghan in :issue:`1263917`, :issue:`1263918`.)

Overall visual improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Recipe results are no longer displayed inline on the job page. This change is
the basis for future features allowing users to compare multiple selected
recipes.

Beaker 23 follows the same style used for systems, rendering quick info boxes
for job and recipe pages. These info boxes provide essential information for the
user about the job and recipe, as well as quick access to job activity and the
system the job is running on.


Recipe sets can now be directly referenced
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can now link directly to recipe sets on the job page. A small anchor symbol
appears when hovering over the recipe set or recipe id, allowing to copy the URL
and sharing it in emails and bug reports.

Access to more information
~~~~~~~~~~~~~~~~~~~~~~~~~~

The previous Beaker web UI was not showing important information like generated
kernel options which Beaker passed to Anaconda or task parameters.

Beaker 23 now shows information about:

* Job submitter
* Installation options specified in the job XML
* Scheduler settings specified in the job XML for ``autopick`` and ``watchdog``
* Generated kernel options which Beaker passed to Anaconda.
* Task parameters. This is particularly important when a recipe runs multiple
  instances of the same task with varying parameters.
* Recipe roles and task roles.

Improved access to logs
~~~~~~~~~~~~~~~~~~~~~~~

Previously, failed results remained collapsed on the recipe page making it
harder for users to find the cause for a failure at first glance.

In Beaker 23, the improved recipe page allows you to focus on finding
failures quickly. The recipe page provides quick access to logs for the first failed
task as well as the console output for finding hardware related issues.

Better support for comments and waiving results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For users who needed to indicate false positives for colleagues, former Beaker
versions only provided rudimentary support for waiving of results in the web UI.
Furthermore, you could only leave one comment on a recipe set and the page did
not indicate whether any comment was already present.

With Beaker 23, we have included first class support for commenting on tasks and
recipes, as well as waiving recipe sets.

You can now add comments by clicking on the speech-bubble icon on the recipe or
job page. The comments can use Markdown formatting providing additional support
to link to corresponding issues or web sites.

Markdown for whiteboards and comments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users who kick off jobs in Beaker from a CI environment like Jenkins typically
use the whiteboard field in Beaker to supply important information about the
scheduled job and/or recipe. The whiteboard field of previous Beaker versions
never provided room for adding more information than just one line, which is
sometimes too little.

Beaker 23 adds support for multi-line whiteboard fields, formatted as Markdown,
which will be useful to provide links referencing CI jobs or additional
information about the scheduled Beaker job.

Deleted jobs can be viewed
~~~~~~~~~~~~~~~~~~~~~~~~~~

The old user interface did not provide support for cloning deleted jobs, while
the improved job page allows to visit the deleted job. Even though the results
of the deleted job are gone, one frequent use case is to clone the job, make
modifications and re-schedule it again.

Preferences user interface improvements
---------------------------------------

If your Beaker account is managed by an external authentication service
(such as Kerberos or LDAP) the web UI no longer offers to let you
change your password. In previous versions of Beaker the web UI would
show a field for changing your password, but using it would fail.

The user preferences page has also been improved. Now when you update your root
password, the page will indicate how long ago you updated it and its new
expiry time.

(Contributed by Dan Callaghan in :issue:`1019177` and :issue:`1175586`.)

Beaker client improvements and bug fixes
----------------------------------------

Subcommands are loaded from setuptools entry points
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Third-party packages can now supply their own bkr subcommands by defining 
a setuptools entry point in the ``bkr.client.commands`` group. The name of the 
entry point is used as the subcommand name, and the entry point itself must be 
a subclass of :py:class:`bkr.client.BeakerCommand`.

Previously the only way for packages to provide their own subcommand was to 
drop a module into the ``bkr.client.commands`` package, following certain 
naming conventions. This mechanism of loading subcommands is still supported 
for backwards compatibility.

Managing lab controllers
~~~~~~~~~~~~~~~~~~~~~~~~

This release adds the ability to use the :program:`bkr` client program to create
(by using ``labcontroller-create``) and modify (by using
``labcontroller-modify``) lab controllers.

(Contributed by Matt Jia in :issue:`1211119` and :issue:`1337812`.)

Client bug fixes
~~~~~~~~~~~~~~~~

* :issue:`1229966`: The :program:`bkr` client now supports ``--pretty-xml`` and ``--dry-run`` options for the following commands:

  * :program:`bkr job-clone`,
  * :program:`bkr job-watch`,
  * :program:`bkr update-inventory`.

  The :program:`bkr job-submit` command supports now ``--dry-run``.
  (Contributed by Blake McIvor)

* :issue:`1336966`, :issue:`1328313`: The :program:`bkr group-modify` command is
  now more reliable if multiple options of ``--remove-member`` or
  ``--add-member`` are specified.
  (Contributed by Blake McIvor)

* :issue:`1323921`: You can now set ``AUTH_METHOD="none"`` in the client
  configuration file to make :program:`bkr` skip any attempt at authentication.
  This is useful for automated tools which want to perform read-only requests
  against Beaker, for example workflow commands with the :option:`--dry-run <bkr --dry-run>`
  option.
  (Contributed by Dan Callaghan)

* :issue:`990943`: The :option:`bkr job-delete --completeDays` option is now
  consistent with the same option for :option:`bkr job-list <bkr job-list --completeDays>`.
  (Contributed by Blake McIvor)

* :issue:`1323885`: A new command :program:`bkr system-create` has been added to
  allow creating systems using bkr client.
  (Contributed by Matt Jia)

* :issue:`1268811`: The :program:`bkr system-modify` command now returns a
  non-zero exit status if no FQDN is given, indicating that no action was
  performed.
  (Contributed by Blake McIvor)


Other new features and enhancements
-----------------------------------

The beaker-pxemenu utility now generates GRUB2 menus for x86 EFI systems.
(Contributed by Matt Jia in :issue:`1087090`.)

The web UI now also supports searching for systems associated to a certain lab
controller. (Contributed by Hao Chang Yu in :issue:`704399`)

It is now possible for ``<hostRequires/>`` to match systems on the total number
of disks within a system using ``<disk_count/>``. (Contributed by Blake McIvor in
:issue:`1216257`)

The job results XML now includes comments. (Contributed by Dan Callaghan in
:issue:`853351`)

If a job is deleted, the ``recipe_task_result`` rows are also deleted keeping
the database size small. (Contributed by Matt Jia in :issue:`1322700`)

Beaker now supports a Markdown formatted group description. The description can
be helpful to add arbitrary information on requesting group membership. It is
managed by using either :program:`bkr group-modify` or the web UI.
(Contributed by Matt Jia in :issue:`960359`.)

Bug fixes
---------

A number of bug fixes are also included in this release:

* :issue:`1293011`: :program:`beaker-log-delete` does not crash anymore, if it
  attempts to delete logs for jobs with a very large set of results.
  (Contributed by Dan Callaghan)

* :issue:`1284368`: The reserve workflow now validates the requested duration,
  only allowing to reserve the system to a maximum of 99 hours enforced by
  ``/distribution/reservesys``. (Contributed by Róman Joost)

* :issue:`1321740`: The columns on the systems page are now ordered
  alphabetically. Previously their order was arbitrary and could change between
  page loads. (Contributed by Róman Joost)

* :issue:`554844`: The user-guide has been updated with a chapter on how to
  create a Beaker task with restraint.
  (Contributed by Róman Joost)

* :issue:`888136`: A troubleshooting section has been added to the user guide.
  (Contributed by Róman Joost)

* :issue:`1322219`: The ``rhts-abort`` command no longer leaves a task in a
  ``Completed`` state rather than ``Aborted``.
  (Contributed by Dan Callaghan)

* :issue:`1257062`: A new ``conditional`` skeleton has been added to :program:`beaker-wizard`.
  (Contributed by Dan Callaghan)

* :issue:`1087225`: The :program:`beaker-provision` daemon has been made more resilient
  for longer server down times.
  (Contributed by Matt Jia)

* :issue:`1339034`: Beaker administrators can now update the email address and
  password for the user account associated with the lab controller on the lab
  controller page. (Contributed by Matt Jia)

* :issue:`1328153`: Previously, passing ``harness=restraint-rhts`` for a recipe
  on IA64 would cause the restraint-rhts.i386 package to be installed, resulting
  in SELinux denials. Beaker now uses yum's ``multilib_policy=best`` setting
  when installing harness packages on IA64 in order to avoid installing .i386
  packages in compatibility mode.
  (Contributed by Dan Callaghan)

* :issue:`1335370`: You can now type :kbd:`Ctrl-Enter` in any text area to submit
  the form.
  (Contributed by Blake McIvor)

* :issue:`1319988`: The option ``--ignore-system-status`` is now accepted by all
  :program:`bkr` workflow commands.
  (Contributed by Matt Jia)

* :issue:`1333516`: Latest Fedora 24 armhfp can be imported with :program:`bkr distro-import`.
  (Contributed by Bill Peck)

* :issue:`1337790`: The :program:`beaker-init` tool will now delete left over
  ``log_recipe_task_result`` rows for deleted jobs.
  (Contributed by Matt Jia)

* :issue:`1290273`: Updating the active access policy on a system is not
  reflected in the activity tab if it hasn't changed.
  (Contributed by Matt Jia)

* :issue:`1309906`: The :program:`bkr` client enforces a 2-minute read timeout
  on XML-RPC requests. This prevents it from getting stuck waiting for server
  responses that have been lost, particularly in :program:`bkr job-watch` which
  could end up waiting forever for a job that is already finished. (Contributed
  by Dan Callaghan)

* :issue:`1302942`: The :program:`beaker-init` tool now provides a background mode
  with the ability to monitor the migration.
  (Contributed by Dan Callaghan)

Version 4.70 of ``rhts`` has also been released:

* :issue:`1320320`: ``rhts-reboot`` no longer hangs waiting for user input.
  (Contributed by Dan Callaghan)

The following user interface bugs/RFEs are solved by the job page improvements in this release:

* :issue:`602131`: There is currently no easy way to see the job whiteboard when
  looking at a recipe.

* :issue:`894137`: There is no possibility to directly link to a recipe set in Beaker.

* :issue:`1314271`: Job definitions are not preserved when a job is deleted.

* :issue:`786793`: Task parameters are not visible on the result page.

* :issue:`995009`: Jobs don't show the submitter.

* :issue:`1064738`: Retention tag products can not be repeatedly modified on the
  job page.

* :issue:`872094`: Avoid using cookies to store visible state of recipe results
  on recipe/job page.

* :issue:`1169838`: Job page is broken when visiting ``/jobs/<id>/`` instead of
  ``/jobs/<id>``.

* :issue:`967481`: Commenting on recipe sets which were cancelled before they
  started resulted in a traceback.

* :issue:`646416`: Updating the DOM of the job page results in jerky movements
  of page elements.

* :issue:`1122682`: The comment text area on the jobs page is too small.

* :issue:`1305951`: Comment pop-up on the recipe set is distracting.

* :issue:`1340141`: Allow to turn on reservesys after job submission from the Web UI.

* :issue:`846199`: The recipes page is slow due to unnecessary code querying the database.

* :issue:`1309530`: Beaker shows the reboot time to be a few seconds before the
  recipes start time.
  (Contributed by Dan Callaghan)

* :issue:`626529`: Guest recipes `guestname` and `guestargs` are not visible on
  the recipe page.
  (Contributed by Dan Callaghan)

* :issue:`1165544`: There is no possibility to easily select the tasks version on the recipe page.

.. Not relevant to anyone:

    * :issue:`1298066`: not compatible with SQLAlchemy 1.0: AttributeError: 'SQLiteCompiler' object has no attribute '_get_colparams'
      (Contributed by Róman Joost)
    * :issue:`1324305`: rendering job JSON: AttributeError: 'NoneType' object has no attribute 'microseconds'
      (Contributed by Matt Jia)
    * :issue:`1322700`: delete recipe_task_result rows for deleted jobs
      (Contributed by Matt Jia)
    * :issue:`1301446`: system table has "deleted" column which is never used
      (Contributed by Dan Callaghan)
    * :issue:`1264716`: The :program:`bkr group-modify` command now is using the new HTTP APIs
      introduced in :issue:`1251356`. (Contributed by Matt Jia)

.. Internal or bugs found during development:

    * :issue:`978640`: (Contributed by Dan Callaghan)
    * :issue:`1281587`: [RFE] add SQL queries to Beaker test suite
      (Contributed by Dan Callaghan)
    * :issue:`1326162`: new recipe page takes a long time to render for very large recipes, may trigger Unresponsive Script warning
      (Contributed by Matt Jia)
    * :issue:`1330405`: User have to click cancel button twice in confirm delete dialog
      (Contributed by Blake McIvor)
    * :issue:`1324401`: Firefox sometimes shows a pile of recipe JSON instead of the HTML recipe page when re-opening a closed tab
      (Contributed by Matt Jia)
    * :issue:`1326562`: TypeError: task is null - Recipe link results in blank page instead of access to logs
      (Contributed by Róman Joost)
    * :issue:`1324399`: overflow scroll bars visible on the tasks tab of recipe page
      (Contributed by Matt Jia)
    * :issue:`1335343`: recipe page does not correctly update itself while the recipe is running
      (Contributed by Dan Callaghan)
    * :issue:`1340689`: Cannot waive the recipe set
      (Contributed by Matt Jia)
    * :issue:`1327020`: The Reservation form should allow to specify unit of reservation instead of just seconds
      (Contributed by Róman Joost)
    * :issue:`1346115`: [Webui] Sending empty comment with CTRL+Enter results in two POSTs to the server
      (Contributed by Blake McIvor)
    * :issue:`1348018`: no watchdog for recipe after reboot
      (Contributed by Róman Joost)
    * :issue:`1346586`: downgrading 23.0->22.3 leaves the database in a bad state: ValueError: Invalid value for 'TaskStatus': u''
      (Contributed by Dan Callaghan)

Maintenance updates
-------------------

The following fixes have been included in Beaker 23 maintenance updates.

Beaker 23.1
~~~~~~~~~~~

* :issue:`1362414`: The ``--online-data-migration`` option for
  :program:`beaker-init` has been removed. The data migration is now performed 
  automatically by :program:`beakerd` as necessary as part of each scheduling 
  iteration. This fixes database deadlocks between :program:`beakerd` and the 
  online data migration process which prevent large, heavily utilized Beaker 
  sites from successfully completing the migration. Beaker sites which already 
  upgraded to 23.0 using the original data migration process in 
  :program:`beaker-init` are not affected by this bug. (Contributed by Dan 
  Callaghan)
* :issue:`1362439`: Inefficient ``DELETE`` queries in
  :program:`beaker-log-delete`, introduced in Beaker 23.0, have been fixed. The 
  inefficient queries could impact large Beaker sites causing lock wait 
  timeouts in :program:`beakerd`. (Contributed by Dan Callaghan)
* :issue:`1334552`: Recipe whiteboards are now rendered as Markdown when shown
  on the job page, matching how they are displayed on the recipe page. 
  (Contributed by Matt Jia)
* :issue:`1345735`: The :program:`bkr` client has a new option
  :option:`--insecure <bkr --insecure>` and corresponding configuration setting 
  ``SSL_VERIFY`` which will disable all SSL certificate validity checks, 
  allowing the client to connect to a Beaker server with an invalid or 
  untrusted certificate. (Contributed by Dan Callaghan)
* :issue:`1353825`: The documentation for ``<reservesys/>`` now describes how
  to extend the reservation. (Contributed by Róman Joost)

.. affects tests only:
    * :issue:`1356852`: test_database_migration deadlocks itself on RHEL7 (Contributed by Dan Callaghan)

Version 2.2 of the :program:`beaker-system-scan` hardware scanning utility and 
version 1.2-8 of the ``/distribution/inventory`` task have also been released:

* :issue:`1343347`: The ``kvm_hv`` kernel module is now detected on PowerNV
  systems as indicating support for hardware virtualization. (Contributed by 
  Dan Callaghan)


Beaker 23.2
~~~~~~~~~~~

* :issue:`1366442`: The initial watchdog time for a recipe (after the system is
  first rebooted) is now set to the running time of the first task in the 
  recipe plus 30 minutes. This restores the pre-23.0 behaviour, which was 
  unintentionally changed. (Contributed by Dan Callaghan)
* :issue:`1368509`: The :program:`beaker-transfer` and
  :program:`beaker-watchdog` daemons now re-authenticate to the server only if 
  their session expires. In Beaker 23.0 they were unintentionally 
  re-authenticating every 20 seconds. (Contributed by Dan Callaghan)
* :issue:`1369305`: The :program:`beaker-provision` daemon now correctly
  re-authenticates to the server if its session expires. The fix for 
  :issue:`1087225` in Beaker 23.0 was incomplete. (Contributed by Dan 
  Callaghan)
* :issue:`1362599`: The :guilabel:`Ack` and :guilabel:`Nak` radio buttons on
  the legacy job page have been restored. These were originally removed in 
  Beaker 23.0 as part of the waiving/commenting overhaul. (Contributed by Dan 
  Callaghan)
* :issue:`1368352`: Beaker's Anaconda monitoring script now uploads
  :file:`/tmp/packaging.log` as soon as it is available. Previously under some 
  error conditions the log would not be uploaded back to Beaker. (Contributed 
  by Dan Callaghan)
* :issue:`1197608`: The :program:`bkr` workflow commands now accept a new
  option :option:`--taskfile <bkr --taskfile>` for specifying tasks to be run. 
  Each line in the given file beginning with ``/`` is treated as a task name. 
  (Contributed by Jan Stancek and Róman Joost)
* :issue:`1350959`: The :program:`bkr` client now prints a more helpful error
  message in case the ``CA_CERT`` configuration option refers to a non-existent 
  file. (Contributed by Róman Joost)

Version 4.71 of the ``rhts`` test development and execution library has also 
been released:

* :issue:`1342406`: The ``URL`` field of the RPM metadata is now populated with
  the SCM location of the task's source code. (Contributed by Dan Callaghan)

Version 0.7.10 of the Beah test harness has also been released:

* :issue:`1365853`: The harness no longer considers the Installing status to
  indicate a finished recipe. This fixes a problem where the harness would 
  occasionally skip all tasks in the recipe. (Contributed by Dan Callaghan)

Version 4.0-92 of the ``/distribution/virt/install`` task has also been 
released:

* :issue:`1351666`: The new ``virtlogd`` log rotation functionality in libvirt
  is disabled for Beaker guests, because it prevents the guest console log from 
  being captured. (Contributed by Jan Stancek)


Beaker 23.3
~~~~~~~~~~~

* :issue:`1347239`: Beaker now prevents systems from being set to Automated
  while not associated with any lab controller, since they cannot be used by 
  the scheduler. (Contributed by Róman Joost)
* :issue:`1298055`: The :program:`bkr job-modify` command accepts a new option
  :option:`--whiteboard <bkr job-modify --whiteboard>` to update the whiteboard 
  of an existing job or recipe. (Contributed by Dan Callaghan)
* :issue:`1362596`: The system hostname is now shown for each recipe on the job
  page. (Contributed by Dan Callaghan)
* :issue:`874387`: Systems are no longer marked as broken if the
  ``configure_netboot`` command fails, since that usually indicates a problem 
  with the download URL for the distro rather than a problem with the system. 
  (Contributed by Dan Callaghan)
* :issue:`1375035`: Fixed an edge case with the scheduler's logic for handling
  ``<reservesys/>`` which could cause the reservation to be skipped if the 
  recipe contains only one task which finishes quickly. (Contributed by Róman 
  Joost)
* :issue:`1376645`: A recipe is now marked as "reviewed" only if the recipe
  page is opened after the recipe is finished. Previously a recipe would be 
  marked as reviewed even if it were still running and producing more results. 
  (Contributed by Dan Callaghan)
* :issue:`1369599`: When the scheduler increases the priority of a recipe set
  because it only matches one candidate system, this change is now recorded in 
  the job activity. (Contributed by Dan Callaghan)
* :issue:`1083648`: The :program:`beaker-provision` daemon now only applies the
  quiescent period delay between consecutive ``on`` and ``off`` operations. 
  Previously the delay would also be applied unnecessarily between other 
  commands, such as ``configure_netboot``. (Contributed by Dan Callaghan)
* :issue:`1380600`: The ``/login`` endpoint no longer redirects based on the
  HTTP ``Referer`` header, instead an explicit redirect URL is always passed. 
  This avoids an issue with bad redirects when using mod_auth_mellon for 
  handling authentication in Apache. (Contributed by Dan Callaghan)
* :issue:`1387109`: Beaker now accepts a quiescent period of 0 in the system
  power settings. (Contributed by Dan Callaghan)
* :issue:`1379565`: The Beaker server now avoids looking up its own name in DNS
  whenever possible. Previously the server would perform many DNS lookups of 
  its own name, even when ``tg.url_domain`` was set in the server 
  configuration.  (Contributed by Dan Callaghan)
* :issue:`1364311`: Fixed URL generation to obey the ``server.webpath`` prefix.
  On a number of pages the prefix was not correctly applied, causing HTTP 
  requests in the browser to fail. (Contributed by Jon Orris)
* :issue:`1390412`: Fixed absolute URL generation to obey the ``tg.url_scheme``
  setting in all cases. Previously some pages would include an incorrect URL 
  when the Beaker server is behind an SSL-terminating reverse proxy, causing 
  HTTP requests in the browser to fail. (Contributed by Dan Callaghan)
* :issue:`1350302`: The :program:`beaker-init` tool now considers a database to
  be "empty" even if it contains a lone ``alembic_version`` table. This is to 
  work around the behaviour of :option:`beaker-init --check`, which will create 
  that table when run against an empty database. (Contributed by Jon Orris)
* :issue:`1362598`: The wording of the :guilabel:`Hide Naks` option on the job
  matrix has changed to :guilabel:`Hide Waived` to reflect the changed 
  terminology in Beaker 23. (Contributed by Jon Orris)

Version 1.0-6 of the ``/distribution/virt/image-install`` task has also been 
released:

* :issue:`1333456`: Fixed a regression in parsing guest recipe arguments.
  (Contributed by Jan Stancek)

.. internal only:
    * :issue:`1275109`
