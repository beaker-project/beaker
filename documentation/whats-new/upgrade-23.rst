Upgrading to Beaker 23
======================

These instructions are for administrators upgrading a Beaker installation from 
22 to 23.

Deprecated ``log-delete`` command alias is removed
--------------------------------------------------

In Beaker 0.15, the :program:`log-delete` server utility was renamed to 
:program:`beaker-log-delete` to better reflect its purpose and reduce the 
chance of conflicts. The original :program:`log-delete` command was retained as 
a deprecated compatibility alias.

In this release, the compatibility alias has been dropped. Beaker 
administrators should ensure that any cron jobs or other scripts have been 
updated to use the correct command, :program:`beaker-log-delete`.

Extra data migration step
-------------------------

Beaker 23.0 originally required administrators to invoke a separate data 
migration step by using :program:`beaker-init` with the 
``--online-data-migration`` option.

From Beaker 23.1 onwards, this data migration process is performed 
automatically by :program:`beakerd` and does not require administrators to take 
any action.
