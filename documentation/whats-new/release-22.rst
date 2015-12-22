What's New in Beaker 22?
========================

Beaker 22 adds support for extra job XML elements, JUnit XML results output, 
inverted groups, and many other improvements.


Extra elements preserved in job XML
-----------------------------------

.. highlight:: xml

When a job is submitted Beaker will now accept and preserve any extra XML 
elements which appear at the top level under the root ``<job/>`` node. The 
extra elements must be in an XML namespace in order to distinguish them from 
Beaker job XML elements. The elements and their contents will be stored and 
included in the job results XML and when the job is cloned. The position and 
order of the top-level elements is not preserved.

This is useful for jobs generated with third party tools where extra metadata 
or processing instructions need to be stored with the job and preserved when 
cloning.

For example, the ``<b:option/>`` and ``<f:test/>`` elements in the following 
XML snippet are now legal and will be preserved when cloning the job::

    <job>
        <b:option xmlns:b="http://example.com/bar">--foobar arbitrary</b:option>
        <f:test xmlns:f="http://example.com/foo"><child attribute="" /></f:test>
        <whiteboard>my job</whiteboard>
        [...]

(Contributed by Róman Joost in :issue:`1112131`.)

Job results in JUnit XML format
-------------------------------

The :program:`bkr job-results` command can now export job results in "JUnit 
XML" format (sometimes called "XUnit" format). This results format was 
originally established by the Ant JUnit test runner, and is also understood by 
Jenkins and many other tools. To use the new format, pass 
:option:`--format=junit-xml <bkr job-results --format>`.

If you are running Beaker jobs from within Jenkins, you can use the JUnit XML 
results format with the Jenkins JUnit plugin in order to report your Beaker 
test results in Jenkins.

(Contributed by Dan Callaghan in :issue:`1123244`, :issue:`1291112`, and 
:issue:`1291107`.)

User interface improvements
---------------------------

The web UI for managing groups has been revamped in order to improve 
performance, simplify interactions, and improve code maintainability. The 
improved groups grid also includes more powerful search functionality.

The web UI for administrators to manage lab controllers and power types has 
also been revamped. This also fixes an issue where deleting a power type which 
was still in use would result in a server error.

These enhancements are another small step on the road towards modernizing 
Beaker's web UI using Flask and Backbone.

(Contributed by Matt Jia, Róman Joost, and Dan Callaghan in :issue:`1251356`, 
:issue:`1275999`, :issue:`1251355`, and :issue:`1022461`.)

Inverted groups
---------------

This release introduces a new type of user group, called "inverted groups". An 
inverted group contains all Beaker users by default. The group owner can 
exclude specific users from the group.

For example, a Beaker administrator might create an inverted group named 
``all-humans`` and then add service accounts for scripts and bots to the list 
of excluded users. System owners could then set up their access policies to 
grant permissions to the ``all-humans`` group. This would grant the permissions 
to all Beaker users except the excluded service accounts.

Inverted groups are needed in this case because Beaker's system access policies 
are strictly additive: it is not possible to grant permission to a group while 
also denying it to some members of the group, because the access policies can 
only grant permissions and not deny them.

(Contributed by Matt Jia in :issue:`1220610`.)


Other new features and enhancements
-----------------------------------

Beaker's web UI can now automatically create user accounts for authenticated 
users based on the values of the ``REMOTE_USER``, ``REMOTE_USER_EMAIL``, and 
``REMOTE_USER_FULLNAME`` WSGI environment variables. This is useful for Beaker 
sites which are using centralized authentication but cannot use Beaker's 
existing support for looking up user information in an LDAP directory. For 
example, the Apache modules ``mod_auth_mellon`` (for SAML authentication) and 
``mod_lookup_identity`` (for user lookups using sssd infopipe) can both be 
configured to set the necessary environment variables. (Contributed by Dan 
Callaghan in :issue:`1112925`.)

Beaker now provides stable URLs for all job log files, which will redirect to 
the current storage location. This URL is now used when linking to logs in the 
web UI and in JUnit XML results. This avoids a problem where Beaker would link 
to the logs stored on the lab controller, but by the time a user clicks the 
link the logs have been moved to an archive server and the link is invalid. 
(Contributed by Dan Callaghan in :issue:`1291130`.)

The JSON API for system details now includes detailed CPU and disk information. 
(Contributed by Róman Joost in :issue:`1206033` and :issue:`1206034`.)

The :program:`bkr job-submit` and :program:`bkr job-clone` commands now accept 
a new :option:`--job-owner <bkr --job-owner>` option, for submission delegates 
to submit jobs on behalf of other users. (Contributed by Hao Chang Yu in 
:issue:`1215138`.)

The :program:`bkr job-modify` command now accepts a new :option:`--priority 
<bkr job-modify --priority>` option, for changing the priority of a queued job 
or recipe set. (Contributed by Matt Jia in :issue:`1149977`.)

The :guilabel:`Reserve` report, which shows how long Beaker systems have been 
reserved for, now has a fully-featured search with the same capabilities as 
other systems grid pages. (Contributed by Róman Joost in :issue:`623562`.)

Notable changes
---------------

Implicit job sharing is disabled
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker 0.13 introduced the :ref:`group jobs <group-jobs-0.13>` feature, which 
allows group members full access to modify, cancel, and delete jobs submitted 
for their group. This was designed to replace the previous "implicit" job 
sharing model where any group member could modify or delete jobs submitted by 
any other member of any group.

Up until this release, the implicit job sharing behaviour was deprecated but 
was still enabled by default unless the Beaker administrator disabled it in the 
configuration. Starting from this release, implicit job sharing is disabled by 
default.

If you were relying on the implicit job sharing permissions, ensure that you 
and your group members submit group jobs. See :ref:`job-access-control`.

Beaker administrators can temporarily re-enable the implicit job sharing 
permissions by setting::

    beaker.deprecated_job_group_permissions.on = True

in :file:`/etc/beaker/server.cfg`, but this is not recommended because the new 
"inverted groups" feature in this release makes it trivial for any user to 
create a group containing all Beaker users, which would give them access to 
modify and delete every Beaker job under the deprecated implicit sharing model.

The implicit job sharing permissions will be deleted entirely in a future 
release.

(Contibuted by Dan Callaghan in :issue:`1280178`.)

Workflow commands no longer force NFS installation by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Previously, when running the :program:`bkr` workflow commands without 
explicitly specifying an installation method using :option:`--method
<bkr --method>`, by default ``method=nfs`` would be added to the recipe 
kickstart metadata, forcing the installation to use NFS.

The workflow commands no longer supply ``method=nfs`` by default. The Beaker 
scheduler will pick the best available installation method. Beaker will still 
prefer NFS when it is available, but if a distro tree is only available over 
HTTP that will be used instead.

(Contributed by Dan Callaghan in :issue:`1220652`.)

Old Cancelled and Aborted jobs will be deleted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Previously the server-side command for deleting expired jobs, 
:program:`beaker-log-delete`, would skip jobs which had no finish time. 
Typically this happens when the job was cancelled or aborted before it was 
scheduled. Such jobs will no longer be skipped and will be deleted according to 
the established job deletion policy.

(Contributed by Dan Callaghan in :issue:`1273302`.)


Bug fixes
---------

A number of bug fixes are also included in this release:

* :issue:`1257020`: When a user account is removed (closed), Beaker now also
  removes the account from all groups and system access policies. Previously 
  the removed user could still appear in groups or policies, even though they 
  had no access to Beaker. (Contributed by Dan Callaghan)
* :issue:`970921`, :issue:`647563`: Fixed an error when adding, removing, or
  changing the numeric flag on key types. (Contributed by Róman Joost)
* :issue:`979270`: Adding duplicate key types is now correctly reported as an
  error. (Contributed by Róman Joost)
* :issue:`1244996`: Beaker versions prior to 0.15 could incorrectly store
  duplicate rows in the ``osmajor_install_options`` table. If such rows still 
  existed in the database it would cause an error when saving OS major install 
  options. This release includes a database migration to correct duplicate rows 
  left behind from old Beaker versions. (Contributed by Dan Callaghan)

.. bugs only affecting unreleased versions/features
   * :issue:`1290266`: Cannot edit a lab controller after creating it (Contributed by Róman Joost)

.. internal only
   * :issue:`1283086`