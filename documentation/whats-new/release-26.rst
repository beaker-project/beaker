What's New in Beaker 26?
========================

Beaker 26 uses Restraint as the default test harness for newer OS releases, 
along with a number of other changes in default behaviour.

Restraint as the default harness
--------------------------------

`Restraint <https://restraint.readthedocs.io/>`_ is now the default test 
harness, for recipes running Fedora 29 and above, and Red Hat Enterprise Linux 
8 and above.

As in previous Beaker releases, you can select a specific test harness by 
defining ``harness=restraint`` or ``harness=beah`` (or any other alternative 
harness package) in the kickstart metadata of your recipes.

For backwards compatibility, Beah remains the default harness on all earlier 
releases (Fedora 28 and earlier, and RHEL7 and earlier). However Restraint is 
also fully supported on these releases, and you can opt in to it if you want to 
transition all your testing to consistently use Restraint.

To coincide with this change, Beaker will no longer populate task requirements 
in the ``%packages`` section of the kickstart, for recipes running Fedora 29 
and above or RHEL8 and above. Restraint will install each task's requirements 
when it executes the task. On earlier releases Beaker will continue to populate 
task requirements in ``%packages`` for compatibility with Beah.

You can override this behaviour by defining ``install_task_requires`` in the 
kickstart metadata for your recipe (or undefining it by using 
``!install_task_requires``). If the variable is defined, task requirements will 
be populated in the ``%packages`` section, causing them to be installed by 
Anaconda.

Additionally, to ease the transition from Beah to Restraint, if a recipe used 
Restraint then Beaker will redirect HTTP requests for task log files named 
:file:`TESTOUT.log` to the corresponding log file produced by Restraint, 
:file:`taskout.log`. This allows external scripts which assume the presence of 
:file:`TESTOUT.log` to continue working unmodified.

(Contributed by Róman Joost in :issue:`1589610` and :issue:`1589614` and Dan 
Callaghan in :issue:`1622805`.)

New task for installation checking
----------------------------------

Beaker now provides a new task, ``/distribution/check-install``, for collecting 
diagnostic information about the installation which was done at the start of 
each recipe. It replaces the existing ``/distribution/install`` task which is 
now deprecated.

The new task name is intended to reduce confusion about the purpose of the task 
(it is not installing an operating system, it is just reporting back on the 
installation which Beaker has done).

The new task also carries a very minimal dependency footprint, unlike the 
original ``/distribution/install`` task which installs a significant number of 
unnecessary packages for historical reasons.

The existing ``/distribution/install`` task remains unchanged and will continue 
to be supported. The :program:`bkr` workflow commands will now schedule 
``/distribution/check-install`` as the first task in the recipe for Fedora 29 
and above and RHEL8 and above. They will continue to schedule 
``/distribution/install`` as the first task in the recipe for Fedora 28 and 
earlier and RHEL7 and earlier. Other tools which submit jobs to Beaker can 
switch to using ``/distribution/check-install`` at their discretion.

(Contributed by Dan Callaghan in :issue:`1188539`.)

Recipes without pre-built harness packages
------------------------------------------

By default, when Beaker provisions a system it will configure a Yum repository 
named ``beaker-harness`` which contains the test harness and other packages to 
be installed on the systems under test.
This repo is served from the :file:`/var/www/beaker/harness/{osmajor}/` 
directory on the Beaker server. See :doc:`beaker-repo-update 
<../admin-guide/man/beaker-repo-update>` for the administrative command to 
populate the harness repos.

If Beaker cannot find a suitable harness repo for a given recipe, it will abort 
the recipe with the message "Failed to find repo for harness".

However, in some cases it is not desired or expected that Beaker should provide 
harness packages for the recipe. For example, when using the "contained 
harness" support (see :doc:`../user-guide/contained-test-harness`), or when 
using a custom distro which is not compatible with existing releases.

Beaker now supports a new kickstart metadata variable, 
``no_default_harness_repo``. If you define this variable, Beaker will not 
configure the ``beaker-harness`` Yum repository and it will not check that any 
suitable harness packages are cached on the server. You should ensure that you 
supply working harness packages in some other way, for example by configuring 
your own harness repo using the ``<repo/>`` element in your job XML.

(Contributed by Róman Joost in :issue:`1599136`.)

Bug fixes
---------

A number of bug fixes are also included in this release:

* :issue:`1625234`: The :program:`anamon` installer monitoring script will not
  attempt to run the Python 3 version of the script in 
  :file:`/usr/libexec/platform-python` if it is a Python 2 interpreter (which 
  is the case in RHEL7.6). In that situation, it will fall back to running the 
  Python 2 version of the script in :file:`/usr/bin/python` as before. 
  (Contributed by Jeffrey Bastian)
* :issue:`1620334`: Beaker now accepts integers of up to 10 digits for the
  "score" when a task is reporting a result. Previously the score was limited 
  to 8 digits, and would be recorded as 99999999 if a value with more than 
  8 digits was given. (Contributed by Dan Callaghan)
* :issue:`1630884`: Beaker now accepts strings of up to 241 characters for the
  firmware version field in device information. Previously a version string of 
  more than 32 characters (which is uncommon but not impossible) would cause 
  the hardware scan to fail with a DataError exception. (Contributed by Dan 
  Callaghan)
* :issue:`1624909`: The :program:`beaker-wizard` utility now accepts CVE
  identifiers with 4 or more digits after the year portion (for example, 
  CVE-2018-10000). Previously it expected the numeric portion to be exactly 
  4 digits. (Contributed by Róman Joost)
* :issue:`1297603`: The internal database representation of "dirty" jobs has
  been changed and the query used by the scheduler to find them has been 
  simplified, in order to improve the scheduler's performance. (Contributed by 
  Dan Callaghan)
* :issue:`991269`: The :program:`beaker-watchdog` daemon has been restructured
  to use gevent and its error handling has been improved. Previously the daemon 
  would crash with no useful log messages when it encountered certain error 
  conditions from the Beaker server. (Contributed by Dan Callaghan)
* :issue:`1622753`: Beaker now passes the ``-d 1`` option when it is invoking
  :program:`yum` commands on RHEL4, to prevent older versions of yum from 
  printing a large number of hashes to the serial console as part of its 
  progress bars. Newer versions of yum use a less noisy progress bar 
  implementation and so this option is not required on RHEL5 and above. 
  (Contributed by Dan Callaghan)

.. internal workflow so it is not published in the release notes:
   :issue:`1626316`

Maintenance updates
-------------------
The following fixes have been included in Beaker 26 maintenance updates.

Beaker 26.1
~~~~~~~~~~~
* | :issue:`1618344`: Previously, the /distribution/virt/install task would fail
    to install the guest on RHEL8 because Python 2 was not available. The task
    now correctly requires a Python 2 interpreter. 
  | (Contributed by Dan Callaghan)
* | :issue:`1619545`: Previously, the /distribution/reservesys task would fail
    to send email when the system was ready on RHEL8 recipes. The task now 
    correctly starts the Postfix MTA on RHEL8.
  | (Contributed by Dan Callaghan)
* | :issue:`1640892`: In Beaker 26.0, the default harness for RHEL-ALT-7 was
    unintentionally changed to Restraint. The default harness for RHEL-ALT-7 has
    been fixed to use Beah.
  | (Contributed by Bill Peck)
* | :issue:`1642525`: The :program:`beaker-init` tool now recognizes 26 as a
    valid Beaker version.
  | (Contributed by Chris Beer)
* | :issue:`1643139`: Fixed a regression introduced in Beaker 26 which caused a
    'RuntimeError: dictionary changed size during iteration' failure to appear
    in the :program:`beaker-watchdog` logs. 
  | (Contributed by Chris Beer)


Beaker 26.2
~~~~~~~~~~~
* | :issue:`1638258`: Previously, kickstart installation would fail
    with ks_meta=manual. Kickstart command ignoredisk --interactive
    is used in manual mode, however option --interactive is deprecated.
    Beaker kickstart file now correctly contains kickstart command ignoredisk
    without --interactive option.
  | (Contributed by Martin Styk)
* | :issue:`1644032`: Previously, the /distribution/reservesys task would fail
    with option RESERVE_IF_FAIL and always reserves all systems. The task now
    correctly reserves a system only when one of the previous task fail. 
  | (Contributed by Martin Styk)
* | :issue:`1636550`: To increase the reliability of installations on S390x
    Beaker added --cdl option to the clearpart kickstart command.
  | (Contributed by Martin Styk)
* | :issue:`1652476`: Previously, :program:`beaker-repo-update` would fail to
    update repositories because the default URL was incorrect. 
    :program:`beaker-repo-update` now uses correct default URL.
  | (Contributed by Martin Styk)
* | :issue:`1650337`: Updated internal test code to use new URL for dogfood jobs
  | (Contributed by Chris Beer)
* | :issue:`1579161`: The :program:`beaker-expire-distros` tool now accepts
    dry-run parameter.
  | (Contributed by Martin Styk)
* | :issue:`1656272`: Improved grammar in :program:`beaker-wizard`.
  | (Contributed by Martin Styk)
* | :issue:`1653339`: Added documentation for limit parameter in :program:`bkr`
    group-list.
  | (Contributed by Martin Styk)
* | :issue:`1652641`: Previously, beaker client would fail to add a task to 
    Beaker task library because the task contained binary data. 
    Beaker client now allows adding a task containing binary data. 
  | (Contributed by Martin Styk)


Beaker 26.3
~~~~~~~~~~~
* | :issue:`1566859`: Retired Piwik integration with Beaker.
  | (Contributed by Martin Styk)
* | :issue:`1614171`: Beaker now gives 404 when accessing a non-existent task.
  | (Contributed by Tomas Klohna)
* | :issue:`1663317`: Previously, Beaker Jenkins Jobs (BJJ) contained deprecated
    commands. BJJ now uses up-to-date commands.
  | (Contributed by Chris Beer)
* | :issue:`968828`: Created documentation for :program:`beaker-log-delete`.
  | (Contributed by Martin Styk)
* | :issue:`1663121`: BJJ now uses unified Koji instance.
  | (Contributed by Martin Styk)
* | :issue:`978824`: Extended documentation for importing distros.
  | (Contributed by Tomas Klohna)
* | :issue:`1664750`: Beaker now allows to remove/disable repo by Repo ID. You
    can find which repo IDs are available for a particular distro tree under the 
    Repos tab on the distro tree page.
  | (Contributed by Martin Styk)


Beaker 26.4
~~~~~~~~~~~
* | :issue:`1181320`: All logged in users can now report a problem with working 
    system.
  | (Contributed by Tomas Klohna)
* | :issue:`1676571`: Removed command ignoredisk from kickstart for RHEL8+ and
    Fedora 29+.
  | (Contributed by Martin Styk)
* | :issue:`1635309`: Fixed a regression in scheduler which caused job abort in 
    case of using <distro> tag and specific host machine.
  | (Contributed by Martin Styk)
* | :issue:`1602251`: Beaker now captures syslog/journal messages produced 
    during the installation.
  | (Contributed by Martin Styk)
* | :issue:`1655770`: System pages show LoanedTo column for easier readability.
  | (Contributed by Tomas Klohna)
* | :issue:`1685598`: Added support for systemd :program:`anamon`.
  | (Contributed by Tomas Klohna)
* | :issue:`1604418`: Beaker now correctly populates 
    :file:`/root/NETBOOT_METHOD.TXT` even when perl is missing.
  | (Contributed by Martin Styk)
* | :issue:`1667340`: Pool names are sorted alphabetically.
  | (Contributed by Tomas Klohna)
* | :issue:`1616163`: Possible systems page shows LoanedTo column for easier
    readability.
  | (Contributed by Tomas Klohna)
* | :issue:`1689926`: Updated :program:`restraint` BJJ to use static build 
    from fetched tarballs.
  | (Contributed by Martin Styk)

.. internal workflow so it is not published in the release notes:
   :issue:`1666204`, `1678595`


Beaker 26.5
~~~~~~~~~~~
* | :issue:`1697479`: Fixed a regression in :program:`anamon` which caused
    extensive writing to logs.
  | (Contributed by Martin Styk)
* | :issue:`1695029`: Previously, Beaker used program:`yum` in generated
    kickstarts. Now, Beaker uses :program:`dnf` when it is available in OS
    distribution.
  | (Contributed by Martin Styk)
* | :issue:`1043419`: Job Matrix no longer failing with code 500 Internal Error
    when Job ID field contains non-integer chars.
  | (Contributed by Tomas Klohna)
* | :issue:`1175584`: Removed ability to store duplicate SSH key in Web UI.
  | (Contributed by Tomas Klohna)
* | :issue:`1672048`: Added MODULE key to Key/Value search in Web UI.
  | (Contributed by Tomas Klohna)
* | :issue:`1229802`: Added Notes column to search in Web UI.
  | (Contributed by Tomas Klohna)
* | :issue:`1414669`: Beaker client now allows to filter by group in job-list
    command.
  | (Contributed by Tomas Klohna)
* | :issue:`1362048`: Task names are fully visible and no longer cropped in Web
    UI.
  | (Contributed by Tomas Klohna)
* | :issue:`1597923`: Beaker client now supports JSON output for system-details
    command.
  | (Contributed by Carol Bouchard)
* | :issue:`1688877`: Provisioning system through Reserve System no longer creates
    Job with an empty whiteboard by default.
  | (Contributed by Carol Bouchard)
* | :issue:`1409676`: Added support for :program:`product-update` script to send
    Accept header in HTTP requests.
  | (Contributed by Tomas Klohna)
* | :issue:`1384491`: Previously, Beaker Lab Controller (LC) daemons couldn't
    start due to issue in python-gevent package on RHEL 7. Beaker now uses
    python-gevent package which is not causing any issues in LC daemons.
  | (Contributed by Martin Styk)
* | :issue:`1686147`: Updated documentation for Job XML definition.
  | (Contributed by Carol Bouchard)
* | :issue:`1654848`: Extended OpenStack support.
  | (Contributed by Chris Beer)

.. internal workflow so it is not published in the release notes:
   :issue:`1707057`, `1693758`

Beaker 26.6
~~~~~~~~~~~
* | :issue:`1704804`: Extended beaker-wizard to accept full OSMajor distro names.
  | (Contributed by Carol Bouchard)
* | :issue:`1719829`: Watchdog no longer report user domain general protection fault
  | as panic.
  | (Contributed by Tomas Klohna)
* | :issue:`1751105`: Added support to remove all distributions from Lab Controller.
  | (Contributed by Martin Styk)
* | :issue:`1758124`: Fedora 31+ disabled root password login in SSH. This patch
  | enables it again to provide consistent experience on all systems under test.
  | (Contributed by Martin Styk)
* | :issue:`1724650`: Fixed race conditions between Python 2.6 and Python 2.7.
  | (Contributed by Martin Styk)
* | :issue:`1723303`: Power scripts :program:`apc_snmp` and :program:`wti` now
  | supports multiple plugs.
  | (Contributed by Martin Styk)
* | :issue:`1720067`: Added support to run :program:`beaker-expire-distros` on
  | non-local labcontroller.
  | (Contributed by Martin Styk)
