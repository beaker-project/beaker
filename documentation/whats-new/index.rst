What's New
==========

This document covers major changes to Beaker in each release. It is aimed
at users and administrators of existing Beaker installations that are
being upgraded to a new version.


.. For developers

   During the development cycle, just add new release notes as separate
   files in the appropriate release directory without worrying about
   the relative order. Once the release is declared feature complete
   and ready for formal testing, then wildcard entry will be replaced
   with an explicit list that puts the subsections in some kind of
   sensible order.


Unreleased changes
------------------

The following changes will appear in the next Beaker release.

.. toctree::
   :maxdepth: 2
   :glob:

   next/*


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
<http://git.beaker-project.org/cgit/beaker/tree/SchemaUpgrades/>`_ in Beaker's 
source tree. (Those files were previously included in the beaker-server package 
under ``/usr/share/doc/beaker-server-*``.)
