What's New
==========

This document covers major changes to Beaker in each release. It is aimed
at users and administrators of existing Beaker installations that are
being upgraded to a new version.

For general instructions about how to upgrade your Beaker installation to a new 
version, see :doc:`../admin-guide/upgrading`.


.. For developers

   During the development cycle, just add new release notes as separate
   files in the appropriate release directory without worrying about
   the relative order. Once the release is declared feature complete
   and ready for formal testing, then wildcard entry will be replaced
   with an explicit list that puts the subsections in some kind of
   sensible order.

.. Commented out for release:

    Unreleased changes
    ------------------

    The following changes will appear in the next Beaker release.

    .. toctree::
       :maxdepth: 2
       :glob:

       next/*

Beaker 28
---------

Beaker 28 uses Restraint as the default test harness for all OS releases,
iPXE support, enhanced installation failure detection and some other
features.

.. toctree::
   :maxdepth: 2

   release-28

Beaker 27
---------

Beaker 27 has Python 3 support for beaker-common and beaker-client, AMQ messaging,
several changes for outdated packages and some other features.

.. toctree::
   :maxdepth: 2

   release-27

Beaker 26
---------

Beaker 26 uses Restraint as the default test harness for newer OS releases, 
along with a number of other changes in default behaviour.

.. toctree::
   :maxdepth: 2

   release-26

Beaker 25
---------

Beaker 25 adds support for provisioning arbitrary distro trees, Anaconda's 
``liveimg`` command, collecting device firmware versions, and many other new 
capabilities.

.. toctree::
   :maxdepth: 2

   release-25

Beaker 24
---------

Beaker 24 brings improved OpenStack integration, conditional reservations, and many
other improvements.

.. toctree::
   :maxdepth: 2

   release-24

Beaker 23
---------

Beaker 23 provides a new recipe state to reflect the provisioning of a machine, 
generates GRUB2 menus for x86 EFI systems, an improved user experience for job 
and recipe pages, as well as many other improvements.

.. toctree::
   :maxdepth: 2

   release-23
   upgrade-23
   datamining-23


Beaker 22
---------

Beaker 22 adds support for extra job XML elements, JUnit XML results output, 
inverted groups, and many other improvements.

.. toctree::
   :maxdepth: 2

   release-22


Beaker 21
---------

Beaker 21 simplifies the process for system owners to run hardware scans on 
their Beaker systems, reducing it to a single click or CLI command.
This release also includes an improved version of the 
:program:`beaker-system-scan` tool, providing broader hardware support and more 
accurate hardware information for Beaker systems.

.. toctree::
   :maxdepth: 2

   release-21


Beaker 20
---------

Beaker 20 introduces system pools, and the ability to apply the same access 
policy across many systems.
This release also brings support for configurable netboot loaders and several 
other enhancements.

.. toctree::
   :maxdepth: 2

   release-20


Beaker 19
---------

Beaker 19 brings many improvements to the system page. For Beaker 
administrators, the upgrade process has been streamlined with automatic 
database schema upgrades.

.. toctree::
   :maxdepth: 2

   release-19
   upgrade-19


Beaker 0.18
-----------

Beaker 0.18 brings improved usage reminder emails and a new workflow option 
for pre-defined host filters. This release also includes a substantial 
refactoring of Beaker's internal kickstart templates, to provide better support 
for custom distros.

.. toctree::
   :maxdepth: 2

   release-0.18
   upgrade-0.18


Beaker 0.17
-----------

Beaker 0.17 includes two new scheduler features: the capability to schedule 
recipes on systems even when their condition is Manual or Broken, and 
a harness-independent mechanism for reserving systems at the end of their 
recipe.
This release also brings support for theming Beaker's web UI, and experimental 
integration with OpenStack for dynamically created VMs.

.. toctree::
   :maxdepth: 2

   release-0.17
   upgrade-0.17


Beaker 0.16
-----------

Beaker 0.16 adds experimental server-side support for external tasks, 
configurable quiescent periods for system power, and several other 
enhancements.

.. toctree::
   :maxdepth: 2

   release-0.16
   upgrade-0.16


Beaker 0.15
-----------

Beaker 0.15 introduces the concept of "system access policies", the initial
phase of the `Access Policies for Systems
<../../dev/proposals/access-policies-for-systems.html>`__
design proposal. It also includes a major update to the main web UI, along
with a number of other new features and bug fixes.

.. toctree::
   :maxdepth: 2

   release-0.15
   upgrade-0.15


Beaker 0.14
-----------

Beaker 0.14 introduces the concept of "submission delegates", completing
the development of the
`Enhanced User Groups <../../dev/proposals/enhanced-user-groups.html>`__
design proposal. It also includes a number of other new features and bug
fixes.

.. toctree::
   :maxdepth: 2

   release-0.14
   upgrade-0.14


Beaker 0.13
-----------

Beaker 0.13 includes a number of new features and bug fixes, focusing on
the `Enhanced User Groups <../../dev/proposals/enhanced-user-groups.html>`__ 
design proposal.

.. toctree::
   :maxdepth: 2

   release-0.13
   upgrade-0.13

Beaker 0.12
-----------

Beaker 0.12 includes a number of new features and bug fixes.

.. toctree::
   :maxdepth: 2

   release-0.12
   upgrade-0.12

Beaker 0.11
-----------

Beaker 0.11 brings improvements to reporting and metrics collection, as well as 
a number of minor enhancements and bug fixes.

.. toctree::
   :maxdepth: 2

   release-0.11
   upgrade-0.11

Beaker 0.10
-----------

Beaker 0.10 adds experimental support for running recipes on oVirt guests, plus 
enhancements to scheduling of guest recipes and many other bug fixes.

.. toctree::
   :maxdepth: 2

   release-0.10
   upgrade-0.10

Beaker 0.9
-----------

Beaker 0.9 introduces a new "native" provisioning mechanism, instead of using 
Cobbler. The 0.9.x release series also includes a number of other enhancements 
and bug fixes.

.. toctree::
   :maxdepth: 2

   release-0.9
   upgrade-0.9

Older releases
--------------

Release notes for versions prior to 0.9 are not available.

For administrators upgrading from older versions, refer to the now-obsolete 
`SchemaUpgrades directory 
<https://github.com/beaker-project/beaker/tree/master/SchemaUpgrades/>`_ in Beaker's
source tree. (Those files were previously included in the beaker-server package 
under ``/usr/share/doc/beaker-server-*``.)
