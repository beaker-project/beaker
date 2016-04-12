Run commands-for-recipe-installations data migration step
=========================================================

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
