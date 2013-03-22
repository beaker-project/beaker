Task name is UNIQUE and limited to 255 characters
=================================================

To update the ``task`` table with the ``UNIQUE`` constraint on ``name``, run the following SQL::

    ALTER TABLE task
        MODIFY name VARCHAR(255) UNIQUE;

.. admonition:: Remove duplicate tasks

   Since the ``task`` table may already contain tasks with duplicate
   names, it is a good idea to first remove them::

       DELETE FROM task USING task, task AS vtask
           WHERE task.id<vtask.id AND task.name=vtask.name;

The above SQL query will keep the task with the maximum task ID (most
recent one) and remove the others having the same name.

For rollback, run the following SQL::

    ALTER TABLE task
        DROP INDEX name;

    ALTER TABLE task
        MODIFY name VARCHAR(2048);

New tests should be written such that their names do not exceed the ``255`` character limit.

Related bugs:
 
- :issue:`915549`
