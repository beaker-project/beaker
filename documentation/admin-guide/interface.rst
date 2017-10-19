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

You can also grant special system-wide permissions to groups. These permissions 
would typically only be granted to special groups for service accounts or 
privileged users. The following permissions are defined:

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
    change_prio
        Permitted to increase or decrease the priority of any user's job.

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


.. _admin-export:

Export
------

The :menuselection:`Admin --> Export` menu item allows an
administrator to export data about the systems and user
groups as CSV files. Currently, the following data can be exported:

Systems
    For every system, its FQDN, its deletion and secret status, lender,
    location, MAC address, memory, model, serial, vendor, supported
    architectures, lab controller, owner, status, type and cc fields
    are exported.

Systems (for modification)
    In addition to the above fields, this also exports the database
    identifier for each system. This is useful when you want to rename
    existing systems (see :ref:`admin-import`).

System LabInfo
    For every system, the original cost, current cost, dimensions,
    weight, wattage and cooling data about its lab is exported. If
    there is no such data available for this system, the corresponding
    system entry is not exported.

System Power
    For every system, the power address, username and password, power
    id and power type are exported.

System Excluded Families
    The data for systems which are excluded from running jobs requiring certain
    families of operating systems are exported. The fields exported
    are the FQDN of the system and the details about the operating system
    (architecture, family and the update) which is excluded.

System Install Options
    The data for the systems with custom install options are
    exported. The fields exported are the FQDN of the system,
    architecture, the operating system family (and update) and the
    corresponding install options: ks-meta, kernel options and post
    kernel options.

System Key/Values
    For every system, its key value pairs are exported.

System Pools
    Systems which belong to a system pool are exported along with the
    corresponding pool names.

User Groups
    The users and the groups which they are a member of are exported.


.. _admin-import:

Import
------

The :menuselection:`Admin --> Import` option is useful for two
workflows:

1. Administrator exports the data from a Beaker instance (see
   :ref:`admin-export`), makes some changes and uploads the modified
   file to the same Beaker instance.
2. Administrator exports the data from a Beaker instance (see
   :ref:`admin-export`) and uses it to setup a new Beaker instance
   (with or without making any changes to the exported data).

The first workflow updates the data about one or more existing systems
or users. For the data related to the systems, the system FQDN is used
to look up the system in Beaker's database. If however, a system is to
be renamed, then the "Systems (for modification)" data should be used
since it also exports the database identifier for the system (the
corresponding field name is "id") which is then used to look up the
system in Beaker's database.

The second workflow is useful when the same set of systems or user
groups should be present in a different Beaker instance. In this case,
the data exported by "Systems (for modification)" should *not* be used
since data about the existing systems may be accidentally overwritten.

.. note::

   The CSV file that can be successfully imported by Beaker must
   conform to the following guidelines:
  
   - The fields are delimited by commas.
   - The values should be quoted with double quotes (for example, ``"Rack 1, Lab 2"``).
   - Quotes are escaped by doubling them (for example, ``"Rack ""A"", Lab 2"``).
