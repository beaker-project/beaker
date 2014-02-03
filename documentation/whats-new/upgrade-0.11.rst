Upgrading to Beaker 0.11
========================

These notes describe the steps needed to upgrade your Beaker installation from 
version 0.10 to version 0.11.


Database changes
++++++++++++++++

.. highlight:: sql

Add new columns to recipe resource table
----------------------------------------

Run the following SQL::

    ALTER TABLE recipe_resource 
        ADD COLUMN rebooted datetime DEFAULT NULL AFTER fqdn,
        ADD COLUMN install_started datetime DEFAULT NULL AFTER rebooted,
        ADD COLUMN install_finished datetime DEFAULT NULL AFTER install_started,
        ADD COLUMN postinstall_finished datetime DEFAULT NULL AFTER install_finished;

To roll back::

    ALTER TABLE recipe_resource
        DROP COLUMN rebooted,
        DROP COLUMN install_started,
        DROP COLUMN install_finished,
        DROP COLUMN postinstall_finished;


Ensure recipe.recipe_set_id and recipe_set.job_id are not NULLable (bug :issue:`881563`)
----------------------------------------------------------------------------------------

If your Beaker database was created prior to version 0.6.14, these two columns
might erroneously permit NULL values. Run the following SQL to correct them::

    ALTER TABLE recipe
        MODIFY recipe_set_id INT NOT NULL;
    ALTER TABLE recipe_set
        MODIFY job_id INT NOT NULL;


Clean up orphaned rendered_kickstart rows (bug :issue:`872001`)
---------------------------------------------------------------

Run the following SQL, to update the foreign key for
recipe.rendered_kickstart_id::

    ALTER TABLE recipe
        DROP FOREIGN KEY recipe_ibfk_4; -- rendered_kickstart_id fk
    ALTER TABLE recipe
        ADD CONSTRAINT recipe_rendered_kickstart_id_fk
        FOREIGN KEY (rendered_kickstart_id)
        REFERENCES rendered_kickstart (id)
        ON DELETE SET NULL;

Then run the following SQL to delete rows from rendered_kickstart which are
associated with deleted recipes::

    DELETE FROM rendered_kickstart
    USING rendered_kickstart
        INNER JOIN recipe ON recipe.rendered_kickstart_id = rendered_kickstart.id
        INNER JOIN recipe_set ON recipe_set.id = recipe.recipe_set_id
        INNER JOIN job ON job.id = recipe_set.job_id
    WHERE job.deleted IS NOT NULL;

To roll back the foreign key change, run the following SQL. There is no
rollback for the row deletions.

::

    ALTER TABLE recipe
        DROP FOREIGN KEY recipe_rendered_kickstart_id_fk;
    ALTER TABLE recipe
        ADD CONSTRAINT recipe_rendered_kickstart_id_fk
        FOREIGN KEY (rendered_kickstart_id)
        REFERENCES rendered_kickstart (id);


Configuration changes
+++++++++++++++++++++

.. highlight:: none

Ensure beaker-proxy can synchronously clear netboot files (bug :issue:`843854`)
-------------------------------------------------------------------------------

Beaker 0.11 installs a configuration file into ``/etc/sudoers.d`` so that
beaker-proxy (running as apache) can clear the TFTP netboot files for
specific servers (owned by root). To ensure that Beaker lab controllers
read this directory, the following command must be enabled in
``/etc/sudoers`` (it is enabled by default in RHEL 6)::

   #includedir /etc/sudoers.d

Note: despite the leading hash character, this really is a command, not a
comment.


Remove identity.provider setting from server.cfg (bug :issue:`880424`)
----------------------------------------------------------------------

Remove the identity.provider setting from ``/etc/beaker/server.cfg`` if present.
The correct value for this setting is supplied by the application configuration
shipped with Beaker.
