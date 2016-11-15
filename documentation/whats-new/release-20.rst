What's New in Beaker 20?
========================

Beaker 20 introduces system pools, and the ability to apply the same access 
policy across many systems.
This release also brings support for configurable netboot loaders and several 
other enhancements.

System pools and shared system access policies
----------------------------------------------

Beaker 20 introduces "system pools" as arbitrary collections of systems.

Previously, a group in Beaker could contain both users and systems. However, 
groups are primarily a way of managing Beaker users. With the introduction of 
system pools, the existing group mechanism becomes exclusively "user groups". 
It is no longer possible to add systems to user groups.

As part of the upgrade to Beaker 20, for each group which contained one or more 
systems, a new system pool will be created with the same name and containing 
the same systems. Pools created during this migration process will have their 
initial description set to "Pool migrated from group <name>" and will be owned 
by the corresponding user group.

Building on the system pools feature, Beaker 20 also makes it possible to share 
a single access policy across a large number of systems. System owners can now 
choose to apply the access policy from a pool, rather than defining the policy 
rules explicitly on their system.

For example, if you own the hardware for the fictional Project Unicorn 
development team, you can create a new Beaker pool named "Project Unicorn". In 
the pool access policy, you can grant reserve permission to the Project Unicorn 
developers. Then you can add each system to the pool, and set them to use the 
access policy from the "Project Unicorn" pool.

Refer to :ref:`system-pools` and :ref:`shared-access-policies` for more 
details.
See also the original :ref:`design proposal 
<beakerdev:proposal-predefined-access-policies>` for further background and 
rationale.

(Contributed by Amit Saha, Matt Jia, and Dan Callaghan in :issue:`1057463`.)

Other new features and enhancements
-----------------------------------

Configurable netboot loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker now supports configuring the netboot loader used on a per-recipe basis, 
by passing ``netbootloader=`` in the kernel options. For example, in ppc64 
recipes Beaker can use yaboot when provisioning older distros and GRUB2 when 
provisioning newer distros. This feature requires that the DHCP configuration 
for the system is updated appropriately.

Refer to :ref:`kernel-options` for details about the ``netbootloader=`` option, 
and to :ref:`boot-loader-images` for details about the new TFTP directory 
layout.

(Contributed by Amit Saha in :issue:`1156036`.)

Workflow commands accept :option:`--reserve <bkr --reserve>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new option :option:`--reserve <bkr --reserve>` is now accepted by 
:program:`bkr` workflow commands. This option adds the ``<reservesys/>`` 
element to each recipe in the job, causing Beaker to reserve the system after 
all tasks have finished executing (or if the recipe is aborted). The duration 
can be controlled using :option:`--reserve-duration <bkr --reserve-duration>`.

For more details about the ``<reservesys/>`` element, refer to 
:ref:`reservesys`.

(Contributed by Dan Callaghan in :issue:`1186719`.)

Workflow commands accept wildcards in :option:`--distro <bkr --distro>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :program:`bkr` workflow commands now treat the value of the 
:option:`--distro <bkr --distro>` option as a SQL LIKE pattern (the % character 
matches any substring).

(Contributed by Bill Peck in :issue:`1200427`.)

:program:`bkr system-modify` can update host hypervisor field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using :option:`bkr system-modify --host-hypervisor` you can update the host 
hypervisor field for a system.

(Contributed by Dan Callaghan in :issue:`1206978`.)

New :option:`--proxy-user <bkr --proxy-user>` option, to authenticate as other users
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option can only be used when the authenticating user is a member of 
a group which has been granted "proxy_user" permission by the Beaker 
administrator. Typically this permission is granted to service accounts so that 
a trusted script can perform actions on behalf of any other Beaker user.

(Contributed by Ján Stanček in :issue:`1199853`.)


Notable changes
---------------

Task roles are now visible between host and guest recipes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In previous Beaker releases, task roles were not visible between the guest 
recipes and the host recipes in a recipe set.

For example, in the following recipe set::

    <recipeSet>
      <recipe system="hostA">
        <task role="SERVERS" />
        <guestrecipe system="guest1">
          <task role="SERVERS" />
        </guestrecipe>
      </recipe>
      <recipe system="hostB">
        <task role="CLIENTS" />
        <guestrecipe system="guest2">
          <task role="CLIENTS" />
        </guestrecipe>
      </recipe>
    </recipeSet>

the role environment variables in both host recipes would have previously 
been::

    SERVERS=hostA
    CLIENTS=hostB

and in both guest recipes they would have been::

    SERVERS=guest1
    CLIENTS=guest2

However, this separation between host and guest recipes has been removed. In 
the above example, all four recipes would see the same role environment 
variables::

    SERVERS=hostA guest1
    CLIENTS=hostB guest2

(Contributed by Dan Callaghan in :issue:`960434`.)

BIOS boot partition is defined in kickstarts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker's kickstart templates now define a 1MB "BIOS boot" partition when:

* the recipe uses custom partitioning (``<partition/>`` or a related
  kickstart metadata variable);
* the system is x86 with BIOS firmware (or EFI firmware running in BIOS
  compatibility mode); and
* the distro supports GPT format disks for BIOS systems (Fedora, CentOS 7,
  RHEL 7).

The BIOS boot partition is needed in case the boot disk is larger than 2TB, 
which causes Anaconda to use GPT instead of MBR when formatting the disk. If 
the boot disk is smaller than 2TB, the BIOS boot partition is still created but 
it will be empty and unused.

(Contributed by Dan Callaghan in :issue:`1108393`.)

:program:`bkr workflow-installer-test` is deprecated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This workflow command was used for submitting jobs to test the Anaconda 
installer. It included support for rendering custom kickstarts on the client 
side using template variables.

Use the :option:`--kickstart <bkr --kickstart>` option for :program:`bkr 
workflow-simple` (or any other workflow command) instead. This option lets you 
pass a kickstart template which is rendered on the server using Beaker's 
existing kickstart templating mechanisms.

Beaker's server-side templating has been expanded to cover all use cases which 
were supported by :program:`bkr workflow-installer-test`, and is now fully 
documented. Refer to :ref:`custom-kickstarts`.

(Contributed by Alexander Todorov and Dan Callaghan in :issue:`1184720`, 
:issue:`966348`, :issue:`1077251`.)

New ``<pool/>`` host filter replacing ``<group/>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the introduction of system pools, a new XML host filter ``<pool/>`` has 
been added for filtering by pool membership. It follows the behaviour of the 
previous ``<group/>`` element, which allowed filtering systems by group 
membership.

For backwards compatibility, the ``<group/>`` element will remain as 
a deprecated alias for ``<pool/>``.

:program:`bkr policy-list` shows active policy by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :program:`bkr policy-list` command now retrieves and prints the rules from 
the system's currently active access policy, which may be a pool policy. If you 
want to retrieve the rules from the system's custom access policy, use the 
:option:`--custom <bkr policy-list --custom>` option.

Changes to reporting queries using ``system_access_policy``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As part of the support for pool access policies described above, the database 
structure for representing system access policies has changed.

If you are running Beaker database queries which join the 
``system_access_policy`` table in order to filter by access policy rules, you 
must update the join condition. Previously the join condition was::

    JOIN system_access_policy
    ON system.id = system_access_policy.system_id

Replace this with::

    JOIN system_access_policy
    ON system.active_access_policy_id = system_access_policy.id


Task and harness updates
------------------------

A new task ``/distribution/rebuild`` has been published, for experimental mass 
rebuilds of the entire distribution from source. See 
:ref:`distribution-rebuild-task`.
(Contributed by Dan Callaghan in :issue:`1183913`.)


Bug fixes
---------

A number of bug fixes are also included in this release:

* :issue:`1207727`: Fixed a regression in Beaker 19.3 with advanced search,
  causing some fields to be incorrectly treated as date fields. (Contributed by 
  Matt Jia)
* :issue:`1109614`: The "post-install done" check-in step in Beaker recipe
  kickstarts now always appears at the very end of the kickstart. Previously in 
  some circumstances it would be performed before all post-install actions were 
  done. (Contributed by Dan Callaghan)
* :issue:`1101817`: Activity pages no longer display a total count of all
  activity records in Beaker, because this is too expensive to compute. 
  (Contributed by Dan Callaghan)
* :issue:`1122464`: The :guilabel:`Executed Tasks` tab on the system page now
  cancels previous AJAX requests before submitting new ones. (Contributed by 
  Matt Jia)
* :issue:`1173376`: The scheduler now correctly clears the candidate system
  mapping for a recipe when it is cancelled or aborted. This prevents a large 
  number of rows needlessly accumulating in the ``system_recipe_map`` database 
  table. (Contributed by Matt Jia)
* :issue:`1149944`: The administration guide now includes a complete copy of
  the :file:`server.cfg` and :file:`labcontroller.conf` configuration files, 
  showing an explanation for each option and its default value. (Contributed by 
  Dan Callaghan)

.. unreleased bugs on develop:
   * :issue:`1202667`: netbootloader= argument is leaked to the kernel (Contributed by Amit Saha)
   * :issue:`1200242`: Add an activity page for System pools (Contributed by Amit Saha)
   * :issue:`1199368`: when a user group is deleted, any pools owned by the group should become owned by the deletor instead (Contributed by Amit Saha)
   * :issue:`1206011`: pool page shows Deleting and then does nothing, when pool name includes # (Contributed by Matt Jia)
   * :issue:`1203981`: My Pools link in menu (Contributed by Matt Jia)
   * :issue:`1203978`: System.can_* methods for permission checking need to use active_access_policy instead of custom_access_policy (Contributed by Amit Saha)
   * :issue:`1199347`: allow system pools to be deleted and renamed (Contributed by Amit Saha)
   * :issue:`1206983`: Update active access policy when a system is removed from a pool (Contributed by Amit Saha)

.. purely internal implementation details:
   * :issue:`1124804`: Switch to SQLAlchemy "back_populates" directive (Contributed by Dan Callaghan)
   * :issue:`1196511`: no released busybox in beaker repos for rhel7 ppc64le (Contributed by Dan Callaghan)

Maintenance updates
-------------------

The following fixes have been included in Beaker 20 maintenance updates.

Beaker 20.1
~~~~~~~~~~~

This release fixes four security vulnerabilities:

* :issue:`1215034`: Modifying key types and power types is now properly
  restricted to Beaker administrators. Previously these operations were 
  unintentionally available to all users, including anonymous users. 
  (Contributed by Matt Jia)
* :issue:`1215020`: DTDs and XML entities are no longer accepted in job XML
  submitted to Beaker. This prevents a type of attack called "XXE" where an 
  authenticated user can cause Beaker to disclose the contents of files on the 
  server's filesystem. (Contributed by Dan Callaghan)
* :issue:`1215030`: Recipe set comments are no longer interpreted as HTML,
  they are now interpreted as plain text and HTML characters are escaped. This 
  prevents authenticated users from performing ``<script>`` injection attacks 
  using recipe set comments. (Contributed by Dan Callaghan)
* :issue:`1215024`: Closing ``</script>`` tags are now properly escaped in the
  JavaScript source for the advanced search bar. (Contributed by Dan Callaghan)


Beaker 20.2
~~~~~~~~~~~

* :issue:`1226076`: Fixed a problem with the handling of ``<group/>`` and
  ``<pool/>`` elements in ``<hostRequires/>`` which would cause the filter to 
  match incorrect systems, and in some cases exhaust temp table space on the 
  database. (Contributed by Matt Jia)
* :issue:`1212517`: The :program:`bkr` client is now compatible with the
  SSL-related changes in Python 2.7.9. (Contributed by Dan Callaghan)
* :issue:`1102442`: The :program:`bkr system-release` command can now also
  release a system which is held by a recipe in Reserved status (using 
  ``<reservesys/>``). (Contributed by Matt Jia)
* :issue:`1181700`: The :program:`bkr system-power` command now accepts
  :option:`--action=none <bkr system-power --action>` in conjunction with 
  :option:`--clear-netboot <bkr system-power --clear-netboot>` to allow 
  clearing a system's netboot configuration without rebooting it. (Contributed 
  by Matt Jia)
* :issue:`1128002`, :issue:`1128004`: Beaker can now perform automatic hardware
  scanning on aarch64 and ppc64le distros. (Contributed by Amit Saha)
* :issue:`1217695`: The pre-defined host filters for the :option:`--host-filter
  <bkr --host-filter>` option have been updated to exclude virtualized systems 
  for CPU-based filters, and a number of new CPU-based filters have been added. 
  (Contributed by Michael Petlan)
* :issue:`1235317`: Beaker now treats Red Hat Gluster Storage 3 like Red Hat
  Enterprise Linux 6 for kickstart templating purposes. (Contributed by Dan 
  Callaghan)
* :issue:`1197074`: The ``<or/>`` and ``<and/>`` elements now have their
  expected effect inside the ``<disk/>`` element in ``<hostRequires/>``. 
  Previously they were ignored. (Contributed by Matt Jia)
* :issue:`1217158`: The :option:`--pool <bkr system-list --pool>` option
  replaces the :option:`--group <bkr system-list --group>` option for
  :program:`bkr list-systems <bkr system-list>`. The old option is still
  accepted as an alias for compatibility. (Contributed by Dan Callaghan)
* :issue:`1219965`: The kickstart templates now define an EFI System Partition
  when using custom partitioning on aarch64, for compatibility with systems 
  which have UEFI firmware. (Contributed by Matt Jia)
* :issue:`1217283`: When a user views the list of systems on the pool page,
  systems which they do not have permission to view will now appear as 
  :guilabel:`(system with restricted visibility)`. (Contributed by Matt Jia)
* :issue:`1213203`: In the list of systems on the pool page, the Remove button
  now correctly appears only when the user has permission to remove the system.  
  Previously the button would always appear. (Contributed by Matt Jia)
* :issue:`1212725`: The :program:`bkr` client now reports a meaningful error
  message when no configuration file was loaded, rather than attempting to 
  connect to localhost. (Contributed by Matt Jia)

Version 1.2-6 of the ``/distribution/inventory`` task has also been released:

* :issue:`1211850`: Fixed false positives in checking if virtualization
  features are disabled by the BIOS, which could occur if the system has "kvm" 
  in its hostname. (Contributed by Amit Saha)

Version 4.66 of the ``rhts`` test development and execution library has also 
been released:

* :issue:`1219920`: The :program:`rhts-lint` command (invoked when building and
  uploading task RPMs) now ignores unrecognised fields in :file:`testinfo.desc` 
  rather than reporting a warning and failing the build. (Contributed by Dan 
  Callaghan)
* :issue:`1219971`: Fixed an issue which would cause :program:`make rpm` to
  incorrectly attempt to upload the task to Beaker when invoked on a Beaker 
  test system. (Contributed by Dan Callaghan)

.. dev only:
   * :issue:`1197917`: tests fail because alembic_version can be created in 
   MyISAM if that is the server default
   * :issue:`1213928`: README is obsolete after split (3b19605)
