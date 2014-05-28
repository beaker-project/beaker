Completed tasks with no result are shown in progress bars
=========================================================

Run the following SQL::

    ALTER TABLE job
    ADD ntasks INT AFTER ttasks;

    ALTER TABLE recipe_set
    ADD ntasks INT AFTER ttasks;

    ALTER TABLE recipe
    ADD ntasks INT AFTER ttasks;

To roll back, run the following SQL::

    ALTER TABLE job
    DROP ntasks;

    ALTER TABLE recipe_set
    DROP ntasks;

    ALTER TABLE recipe
    DROP ntasks;
