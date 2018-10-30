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
* :issue:`1618344`: Previously, the /distribution/virt/install task would fail
  to install the guest on RHEL8 because Python 2 was not available. The task
  now correctly requires a Python 2 interpreter. 
  (Contributed by Dan Callaghan)
* :issue:`1619545`: Previously, the /distribution/reservesys task would fail
  to send email when the system was ready on RHEL8 recipes. The task now 
  correctly starts the Postfix MTA on RHEL8.
  (Contributed by Dan Callaghan)
* :issue:`1640892`: In Beaker 26.0, the default harness for RHEL-ALT-7 was
  unintentionally changed to Restraint. The default harness for RHEL-ALT-7 has
  been fixed to use Beah.
  (Contributed by Bill Peck)
* :issue:`1642525`: The :program:`beaker-init` tool now recognizes 26 as a
  valid Beaker version.
  (Contributed by Chris Beer)
* :issue:`1643139`: Fixed a regression introduced in Beaker 26 which caused a
  'RuntimeError: dictionary changed size during iteration' failure to appear
  in the :program:`beaker-watchdog` logs. 
  (Contributed by Chris Beer)
