Database changes
================

Run the following SQL:

    ALTER TABLE job
        ADD INDEX (status),
        ADD INDEX (result);
    ALTER TABLE recipe_set
        ADD INDEX (status),
        ADD INDEX (result),
        ADD INDEX (priority);
    ALTER TABLE recipe
        ADD INDEX (status),
        ADD INDEX (result);

To roll back, run the following SQL:

    ALTER TABLE job
        DROP INDEX status,
        DROP INDEX result;
    ALTER TABLE recipe_set
        DROP INDEX status,
        DROP INDEX result,
        DROP INDEX priority;
    ALTER TABLE recipe
        DROP INDEX status,
        DROP INDEX result;
