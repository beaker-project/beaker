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

Run commands-for-recipe-installations data migration step
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to the database schema changes for introducing the new 
``installation`` table, there is also a data migration step which is necessary 
to populate historical data in this table. This migration step is potentially 
very slow (more than 24 hours on large Beaker installations) and so it is *not* 
included in the normal automated upgrades done by :program:`beaker-init`.

Instead, :program:`beaker-init` has a new option 
:option:`--online-data-migration=commands-for-recipe-installations
<beaker-init --online-data-migration>` which will perform this data migration. 
The migration is done in batches of 4000 rows (approximately 1 minute each) and 
can be safely interrupted and re-run at any time.

When upgrading your Beaker site, you should follow the usual :doc:`upgrade 
procedure <../../admin-guide/upgrading>` for feature releases, invoking 
:program:`beaker-init` to perform the schema upgrades while Beaker is offline. 
Once the new version of Beaker is online you can then re-run 
:program:`beaker-init` with 
:option:`--online-data-migration=commands-for-recipe-installations
<beaker-init --online-data-migration>` to populate historical data.

(Contributed by Dan Callaghan in :issue:`1302942`)
