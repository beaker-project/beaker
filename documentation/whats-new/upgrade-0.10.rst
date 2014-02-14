Upgrading to Beaker 0.10
========================

These notes describe the steps needed to upgrade your Beaker installation from 
version 0.9 to version 0.10.

Before proceeding with this upgrade, ensure that you have a CSV file to 
re-create your Virtual system records in case you need to roll back. If you 
don't already have one, use Beaker's CSV export feature. If you don't have any 
Virtual system records, ignore this step.

Database changes
++++++++++++++++

Bug :issue:`835367`: running createrepo all the time is inefficient
-------------------------------------------------------------------

There was a change in how we generate repodata so the existing repodata 
directory must be deleted.

::

    rm -rf /var/www/beaker/rpms/repodata

We also need to drop the ``task.oldrpm`` column, but first get a list of old 
RPMs to be deleted::

    mysql $CREDENTIALS beaker -B -N \
        -e 'SELECT oldrpm FROM task WHERE oldrpm IS NOT NULL;' \
        >oldrpms.txt

The RPMs in this list should not be deleted immediately since some existing 
recipes may refer to them and will try to install them. Delete them a few days 
after upgrading.

Now you can run the following SQL to drop the column::

    ALTER TABLE task DROP oldrpm;

To roll back, delete the repodata directory again::

    rm -rf /var/www/beaker/rpms/repodata

and restore the dropped column (but we won't have the old data to restore)::

    ALTER TABLE task
        ADD COLUMN oldrpm VARCHAR(2048) DEFAULT NULL;


Remove system_id from watchdog table
------------------------------------

Run the following SQL::

    ALTER TABLE watchdog
        DROP FOREIGN KEY watchdog_ibfk_4, -- system_id FK
        DROP COLUMN system_id;

To roll back, run the following SQL::

    ALTER TABLE watchdog
        ADD COLUMN system_id INT AFTER id;
    UPDATE watchdog
        INNER JOIN recipe ON watchdog.recipe_id = recipe.id
        SET watchdog.system_id = recipe.system_id;
    ALTER TABLE watchdog
        MODIFY system_id INT NOT NULL,
        ADD CONSTRAINT watchdog_system_id_fk
            FOREIGN KEY (system_id) REFERENCES system (id);


Remove recipe_role and recipe_task_role tables
----------------------------------------------

Run the following SQL::

    DROP TABLE recipe_role;
    DROP TABLE recipe_task_role;

To roll back, run beaker-init to recreate the recipe_role and recipe_task_role
tables, then run the following SQL to populate them::

    INSERT INTO recipe_role (id, recipe_id, role, system_id)
        SELECT NULL, id, role, system_id
        FROM recipe;
    INSERT INTO recipe_task_role (id, recipe_task_id, role, system_id)
        SELECT NULL, recipe_task.id, recipe.role, recipe.system_id
        FROM recipe_task
        INNER JOIN recipe ON recipe_task.recipe_id = recipe.id;


New tables recipe_resource, system_resource, guest_resource (:issue:`655009`)
-----------------------------------------------------------------------------

.. note:: An earlier version of this document (prior to Beaker 0.10.5) used 
   a different query for populating the ``guest_resource`` table which was not 
   correct, see :issue:`882740` for details and corrective action.

First run :program:`beaker-init` to create the new tables, and then run the 
following SQL to populate them.

::

    INSERT INTO recipe_resource (id, recipe_id, type, fqdn)
        SELECT NULL, recipe.id, 'system', system.fqdn
        FROM recipe
        INNER JOIN system ON recipe.system_id = system.id
        WHERE system.type != 'Virtual';
    INSERT INTO system_resource (id, system_id, reservation_id)
        SELECT recipe_resource.id, recipe.system_id, recipe.reservation_id
        FROM recipe
        INNER JOIN recipe_resource ON recipe_resource.recipe_id = recipe.id
            AND recipe_resource.type = 'system';

    INSERT INTO recipe_resource (id, recipe_id, type, fqdn)
        SELECT NULL, recipe.id, 'guest', system.fqdn
        FROM recipe
        INNER JOIN system ON recipe.system_id = system.id
        INNER JOIN machine_guest_map ON machine_guest_map.guest_recipe_id = recipe.id
        INNER JOIN recipe parent ON machine_guest_map.machine_recipe_id = parent.id
        WHERE system.type = 'Virtual'
            AND parent.status NOT IN ('New', 'Processed', 'Queued');
    INSERT INTO guest_resource (id)
        SELECT recipe_resource.id
        FROM recipe
        INNER JOIN recipe_resource ON recipe_resource.recipe_id = recipe.id
            AND recipe_resource.type = 'guest';

    -- set guest recipes back to Queued, if their host is Queued
    DELETE FROM watchdog
        USING watchdog
        INNER JOIN recipe ON watchdog.recipe_id = recipe.id
        INNER JOIN machine_guest_map ON machine_guest_map.guest_recipe_id = recipe.id
        INNER JOIN recipe parent ON machine_guest_map.machine_recipe_id = parent.id
        WHERE parent.status = 'Queued' AND recipe.status != parent.status;
    UPDATE recipe
        INNER JOIN machine_guest_map ON machine_guest_map.guest_recipe_id = recipe.id
        INNER JOIN recipe parent ON machine_guest_map.machine_recipe_id = parent.id
        SET recipe.status = 'Queued'
        WHERE parent.status = 'Queued' AND recipe.status != parent.status;

    ALTER TABLE recipe
        DROP FOREIGN KEY recipe_ibfk_4, -- system_id FK
        DROP COLUMN system_id,
        DROP FOREIGN KEY recipe_reservation_id_fk,
        DROP COLUMN reservation_id;

    DELETE FROM reservation
        USING reservation
        INNER JOIN system ON reservation.system_id = system.id
        WHERE system.type = 'Virtual';
    DELETE FROM system_status_duration
        USING system_status_duration
        INNER JOIN system ON system_status_duration.system_id = system.id
        WHERE system.type = 'Virtual';
    DELETE FROM system_activity
        USING system_activity
        INNER JOIN system ON system_activity.system_id = system.id
        WHERE system.type = 'Virtual';
    DELETE FROM activity
        USING activity
        LEFT JOIN system_activity ON activity.id = system_activity.id
        WHERE type = 'system_activity' AND system_activity.id IS NULL;
    DELETE FROM system
        WHERE type = 'Virtual';
    ALTER TABLE system
        CHANGE type type ENUM('Machine', 'Resource', 'Laptop', 'Prototype') NOT NULL;

To roll back, first restore the dropped columns::

    ALTER TABLE recipe
        ADD COLUMN system_id INT DEFAULT NULL AFTER distro_tree_id,
        ADD CONSTRAINT recipe_system_id_fk
            FOREIGN KEY (system_id) REFERENCES system (id),
        ADD COLUMN reservation_id INT DEFAULT NULL AFTER autopick_random,
        ADD CONSTRAINT recipe_reservation_id_fk
            FOREIGN KEY (reservation_id) REFERENCES reservation (id);
    ALTER TABLE system
        CHANGE type type ENUM('Machine', 'Virtual', 'Resource', 'Laptop', 'Prototype') NOT NULL;

Then use the CSV file you saved to re-create your Virtual system records (if 
you had any). Then run the following SQL to populate the restored columns::

    UPDATE recipe
        INNER JOIN recipe_resource ON recipe_resource.recipe_id = recipe.id
        INNER JOIN system_resource ON recipe_resource.id = system_resource.id
        SET recipe.system_id = system_resource.system_id,
            recipe.reservation_id = system_resource.reservation_id;
    UPDATE recipe
        INNER JOIN recipe_resource ON recipe_resource.recipe_id = recipe.id
        INNER JOIN guest_resource ON recipe_resource.id = guest_resource.id
        INNER JOIN system ON recipe_resource.fqdn = system.fqdn
        SET recipe.system_id = system.id;


Support virtualization managers
-------------------------------

Run the following SQL::

    ALTER TABLE recipe
        ADD COLUMN virt_status
            ENUM('Possible','Precluded','Succeeded','Skipped','Failed')
            NOT NULL DEFAULT 'Possible',
        ADD INDEX (virt_status);

To roll back, run the following SQL::

    ALTER TABLE recipe
        DROP COLUMN virt_status;
