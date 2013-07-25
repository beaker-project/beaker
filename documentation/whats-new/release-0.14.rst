What's New in Beaker 0.14?
==========================

The principle feature added in Beaker 0.14 is the introduction of
"submission delegates", completing the
:ref:`proposal-enhanced-user-groups` design proposal.


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


Fedora 19+ compatibility
~~~~~~~~~~~~~~~~~~~~~~~~

While Beaker has long supported installing Fedora when provisioning a
system, this is the first Beaker release to officially support the use of
Fedora as the server environment for the main Beaker server and the lab
controllers.

The supported server environments for Beaker are now Fedora 19 or later and
RHEL 6 or later.

(Final compatibility fix contributed by Amit Saha in :issue:`977269`)


.. Fedora based Beaker-in-a-box (when merged)

.. Architecture Guide (when merged)


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
