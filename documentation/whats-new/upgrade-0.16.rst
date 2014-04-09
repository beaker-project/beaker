Upgrading to Beaker 0.16
========================

To upgrade the database schema for Beaker 0.16, run the following SQL 
statements.

.. note:: In established Beaker instances the ``recipe_task`` table may be very 
   large, and therefore these upgrade steps may take a long time. Allow 
   approximately 1 minute per 600 000 rows.

::

    ALTER TABLE recipe_task
    ADD name VARCHAR(255) NOT NULL AFTER recipe_id,
    ADD version VARCHAR(255) AFTER name,
    ADD fetch_url VARCHAR(2048) AFTER version,
    ADD fetch_subdir VARCHAR(2048) NOT NULL DEFAULT '' AFTER fetch_url,
    MODIFY task_id INT,
    ADD INDEX (name),
    ADD INDEX (version),
    ADD INDEX (name, version);

    UPDATE recipe_task
    SET name = (SELECT name FROM task WHERE id = recipe_task.task_id);

    ALTER TABLE system_access_policy_rule
    MODIFY permission ENUM('edit_policy', 'edit_system', 'loan_any',
            'loan_self', 'control_system', 'reserve', 'view');

    INSERT INTO system_access_policy (system_id)
    SELECT id FROM system
    WHERE NOT EXISTS (SELECT 1 FROM system_access_policy
        WHERE system_id = system.id);

    INSERT INTO system_access_policy_rule
        (policy_id, user_id, group_id, permission)
    SELECT system_access_policy.id, NULL, NULL, 'view'
    FROM system_access_policy
    INNER JOIN system ON system_access_policy.system_id = system.id
    WHERE NOT EXISTS (SELECT 1 FROM system_access_policy_rule
        WHERE policy_id = system_access_policy.id
            AND user_id IS NULL
            AND group_id IS NULL
            AND permission = 'view')
        AND system.private = 0;

    ALTER TABLE command_queue
    ADD COLUMN (quiescent_period int default NULL),
    ADD INDEX (status);

    ALTER TABLE power
    ADD COLUMN (power_quiescent_period int NOT NULL);

    UPDATE power
    SET power_quiescent_period = 5;

    ALTER TABLE tg_user
    MODIFY password TEXT DEFAULT NULL;

    ALTER TABLE beaker_tag
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (id);

    DROP TABLE locked;
    DROP TABLE serial;
    DROP TABLE serial_type;
    DROP TABLE install;

.. versionchanged:: 0.16.1
   Added missing ``UPDATE`` statement to set the default value for the 
   ``power.power_quiescent_period`` column.

To roll back the upgrade, downgrade the ``beaker-server`` package and run 
:program:`beaker-init` to re-create the dropped tables. Then run the following 
SQL.

Note that rollback is not possible if the external tasks feature has been used 
in your Beaker installation, since it is not possible to satisfy the 
``recipe_task.task_id`` foreign key constraint in that case.

::

    ALTER TABLE recipe_task
    DROP name,
    DROP version,
    DROP fetch_url,
    DROP fetch_subdir,
    MODIFY task_id INT NOT NULL;

    DELETE FROM system_access_policy_rule
    WHERE permission = 'view';

    ALTER TABLE system_access_policy_rule
    MODIFY permission ENUM('edit_policy', 'edit_system', 'loan_any',
            'loan_self', 'control_system', 'reserve');

    ALTER TABLE command_queue
    DROP quiescent_period,
    DROP INDEX status;

    ALTER TABLE power
    DROP power_quiescent_period;

    ALTER TABLE tg_user
    MODIFY password VARCHAR(40) DEFAULT NULL;

    ALTER TABLE beaker_tag
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (id, tag);

Once you are satisfied that the upgrade is successful, you can drop the
obsoleted ``system.private`` column. There is no rollback procedure for this 
step.

::

    ALTER TABLE system DROP private;
