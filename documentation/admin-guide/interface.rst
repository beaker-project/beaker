Beaker interface for administrators
===================================

Some functionality in Beaker’s web interface is restricted to administrators. 
Most of this functionality is accessed from the :guilabel:`Admin` menu.

Groups
------

In addition to the groups functionality available to all users (see 
:doc:`../../user-guide/interface/groups`), administrators have access to 
certain extra features.

If LDAP is configured for identity management (``identity.ldap.enabled`` in the 
server configuration file), you can flag a group's membership to be populated 
from LDAP. If this flag is set, Beaker will not allow users to be added or 
removed from the group manually. Instead, a cron job runs the 
``beaker-refresh-ldap`` command periodically to refresh group membership from 
LDAP. Administrators with command line access to the main Beaker server may also
run ``beaker-refresh-ldap`` directly to force an immediate update from the
LDAP server.

You can also grant additional permissions to groups. These permissions would 
typically only be granted to special groups for service accounts or privileged 
users. The following permissions are defined:

    tag_distro
        Permitted to tag and untag distros.
    distro_expire
        Permitted to remove a distro's association with a lab controller.
    secret_visible
        Permitted to view all systems, including other users' systems which are 
        marked as "Secret".
    stop_task
        Permitted to stop, cancel, or abort jobs or recipe sets owned by any 
        user.

.. _admin-external-reports:

External reports
----------------

If you are using external tools to produce reports about your Beaker site (for 
example, using Beaker's :ref:`Graphite integration <graphite>` or a business 
intelligence tool), you can link to the reports from the "External Reports" 
page in Beaker. Select :menuselection:`Reports --> External` from the menu.

This page displays a grid of links to external reports. When you are logged in 
as an administrator you can also modify the external report links from this 
page.

To add a new report, click :guilabel:`Add Report ( + )` at the bottom of the 
page and fill in the report's name, URL, and a short description to appear 
underneath it.

You can edit or delete a report by clicking the respective link below each 
report.

.. _admin-os-versions:

OS versions
-----------

The "OS Versions" page shows a list of the major and minor versions of every 
distro that has been imported into Beaker. Select :menuselection:`Admin --> OS 
Versions` from the menu.

To edit a particular OS major version, click its name in the first column. From 
this page you can edit the following details:

Alias
    If set, the alias can be used to refer to this OS major version in the 
    ``Releases`` field of task metadata (see :ref:`testinfo-releases`). This is 
    intended mainly as a compatibility mechanism for older tasks which use an 
    obsolete name in the ``Releases`` field (for example ``RHEL3`` instead of 
    ``RedHatEnterpriseLinux3``).

.. note::

   If you set an alias for an existing OS major version, you cannot import distros
   under the aliased name. For example, if you set "RHEL6" as an alias
   for "RedHatEnterpriseLinux6", then attempts to import a new distro
   whose OS major version is "RHEL6" will fail with the following
   error message::

      Cannot import distro as RHEL6: it is configured as an alias for RedHatEnterpriseLinux6

   To fix the problem, either unset the alias or correct the OS major
   version in the distro tree you are trying to import.

Install Options
    These are the default install options when provisioning a distro from this 
    major version. Options may be set for all arches or for each arch 
    individually. Options at this level are overridden by any options set at 
    the distro tree level. See :ref:`install-options` for details about the 
    meaning of these options.

.. _admin-configuration:

Configuration
-------------

Some Beaker configuration is stored in the database rather than in the server 
configuration file, and can be changed without restarting Beaker services. 
Select :menuselection:`Admin --> Configuration` from the menu to view and 
change settings.
