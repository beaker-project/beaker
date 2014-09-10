What's New in Beaker 0.18?
==========================

Beaker 0.18 brings improved usage reminder emails and a new workflow option for 
pre-defined host filters. This release also includes a substantial refactoring 
of Beaker's internal kickstart templates, to provide better support for custom 
distros.


Usage reminder emails
---------------------

A new server side command :program:`beaker-usage-reminder` is now available, 
which sends emails to users to help them keep track of their usage. The emails 
warn about:

* Reservations which are ending soon
* Reservations which have been held for a long time and are blocking other jobs
* Jobs which have been queued for a long time

Beaker administrators can set up a cron job on the Beaker server to send 
reminders at regular intervals using this program. Refer to  
:doc:`beaker-usage-reminder <../admin-guide/man/beaker-usage-reminder>` for 
more details.

This command replaces the previous :program:`beaker-nag-mail` command.

(Contributed by Matt Jia in :issue:`994325`.)


Pre-defined host filters for workflow commands
----------------------------------------------

A new option :option:`--host-filter <bkr --host-filter>` is available for 
:program:`bkr` workflow commands to specify a pre-defined host filter. You can 
use pre-defined host filters as a short-hand for complicated or difficult to 
remember XML snippets. A number of host filters are included with the 
:program:`bkr` client, and users can also define their own host filters.

(Contributed by Amit Saha in :issue:`1081390`.)


Better support for custom distros
---------------------------------

Custom distros (that is, distros which use the Anaconda installer but identify 
themselves as something other than Fedora, Red Hat Enterprise Linux, or CentOS) 
are now treated as equivalent to the latest Fedora release by default. 
Previously it was not possible to use custom distros in Beaker without 
supplying a custom kickstart template (and in some cases, modifying the Beaker 
source code).

There are also a number of new :ref:`kickstart metadata variables 
<kickstart-metadata>` relating to distro features. Administrators can override 
these variables per OS version, and snippet authors can use the variables in 
conditional blocks to handle distro differences.

(Contributed by Dan Callaghan in :issue:`1070597` and :issue:`1132764`.)


Notable changes
---------------

Some kickstart templates removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As part of the improved support for custom distros, the 
:file:`RedHatEnterpriseLinux6`, :file:`RedHatEnterpriseLinux7`, and 
:file:`Fedora` kickstart templates have been removed from Beaker (the 
:file:`default` template is used instead). If you have symlinks in 
:file:`/etc/beaker/kickstarts` for custom distros pointing to the 
:file:`RedHatEnterpriseLinux7` or :file:`Fedora` templates, delete the symlinks 
and Beaker will use the new :file:`default` template.

For custom distros which were using the :file:`RedHatEnterpriseLinux6` 
template, refer to :ref:`distro-features` for guidance about the recommended 
way to handle such distros.

``systemd`` kickstart metadata variable is no longer set
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The undocumented ``systemd`` kickstart metadata variable is no longer populated 
by Beaker. If you have custom kickstart templates or snippets using this 
variable, update them to check if ``has_systemd`` is defined instead.

::

    {% if has_systemd is defined %}
    systemctl ...
    {% endif %}

The ``has_systemd`` variable is one of the new variables relating to distro 
features which were added as part of the improved support for custom distros.
See :ref:`kickstart-metadata`.


Other new features and enhancements
-----------------------------------

When Beaker's experimental :ref:`OpenStack integration <openstack>` integration 
is enabled, the :program:`beaker-watchdog` daemon now captures and stores the 
serial console log for recipes running on dynamic VMs. (Contributed by Matt Jia 
in :issue:`950903`.)

The :program:`bkr job-logs` command has a new option :option:`--size <bkr 
job-logs --size>` to print the size of each log file in the listing. 
(Contributed by Dan Callaghan in :issue:`1128048`.)

The scheduler feature which increases the priority of any recipe matching 
a single system can now be disabled by setting 
``beaker.priority_bumping_enabled = False`` in :file:`/etc/beaker/server.cfg`. 
It remains enabled by default. (Contributed by Dan Callaghan in 
:issue:`978904`.)

A new query for computing utilization for a particular system (or set of 
systems) has been added to the :doc:`supported reporting queries 
<../admin-guide/reporting-queries>`. (Contributed by Amit Saha in 
:issue:`1117681`.)


Task and harness updates
------------------------

Version 4.64 of the ``rhts`` test development and execution library has been 
released, with two changes:

* AVC checking is skipped if SELinux is not enabled. (Contributed by Dan
  Callaghan in :issue:`1126266`.)
* When building a task RPM from a git repository, ``git archive`` is used to
  produce a pristine tarball. Uncommitted modifications in the work tree are no 
  longer included in the task RPM. (Contributed by Dan Callaghan 
  :issue:`1109960`.)

Version 1.2-4 of the ``/distribution/inventory`` task has been released. The 
task will now warn if the system's hardware virtualization features have been 
disabled in firmware. (Contributed by Dan Callaghan in :issue:`738881`.)


Bug fixes
---------

A number of bug fixes are also included in this release.

* :issue:`1108498`: The ``grubport`` kickstart metadata variable now takes
  effect on EFI-based systems. (Contributed by Jun'ichi NOMURA)
* :issue:`1132730`: When a group is deleted, any system access policy rules for
  that group are also deleted. These rule deletions are now reflected in the 
  system activity log. (Contributed by Amit Saha)
* :issue:`1132729`: The :guilabel:`Remove` button on the :guilabel:`My Groups`
  page has been re-labelled :guilabel:`Delete Group` to make its function 
  clearer. (Contributed by Amit Saha)
* :issue:`1120052`: When the scheduler determines that a multi-host recipe set
  cannot be satisfied because not enough systems are available, under some 
  circumstances the recipe set would fail to abort and become stuck in the 
  Processed state. Such recipe sets are now correctly aborted by the scheduler. 
  (Contributed by Dan Callaghan)
* :issue:`1132763`: The :program:`beaker-repo-update` command now skips
  symlinks in the harness repo directory, rather than attempting to update 
  them. (Contributed by Dan Callaghan)
* :issue:`1121763`: The markup on the system page has been adjusted to make it
  easier to copy the system FQDN from the page header. (Contributed by Matt 
  Jia)
