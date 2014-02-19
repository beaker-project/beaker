External tasks
==============

Database changes
----------------

Run the following SQL to upgrade.

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

To roll back, run the following SQL. Note that rollback is not possible if the 
external tasks feature has been used in your Beaker installation, since it is 
not possible to satisfy the ``recipe_task.task_id`` foreign key constraint in 
that case.

::

    ALTER TABLE recipe_task
        DROP name,
        DROP version,
        DROP fetch_url,
        DROP fetch_subdir,
        MODIFY task_id INT NOT NULL;
