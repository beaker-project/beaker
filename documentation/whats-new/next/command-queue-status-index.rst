Add index on ``command_queue.status`` column
============================================

Run the following SQL::

    ALTER TABLE command_queue
        ADD INDEX (status);

To roll back, run the following SQL::

    ALTER TABLE command_queue
        DROP INDEX status;
