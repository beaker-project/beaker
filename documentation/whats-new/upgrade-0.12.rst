Upgrading to Beaker 0.12
========================

Database changes
----------------

Asynchronous job status updates (bug :issue:`807237`)
+++++++++++++++++++++++++++++++++++++++++++++++++++++

Run the following SQL::

    ALTER TABLE job
        ADD COLUMN dirty_version BINARY(16) NOT NULL AFTER id,
        ADD COLUMN clean_version BINARY(16) NOT NULL AFTER dirty_version,
        ADD INDEX ix_job_dirty_clean_version
            (dirty_version, clean_version);
    UPDATE job SET dirty_version = '1111111111111111';

Note that this marks all jobs in the Beaker database as "dirty", which will 
cause beakerd to update their status. This will correct any existing 
inconsistencies in job state, but it will put your Beaker server under higher 
than normal load until this initial pass is complete. The initial pass takes 
approximately 1 hour for every 10,000 jobs.

To roll back, run the following SQL::

    ALTER TABLE job
        DROP COLUMN dirty_version,
        DROP COLUMN clean_version;

Loan comments (bug :issue:`733347`)
+++++++++++++++++++++++++++++++++++

Run the following SQL::

    ALTER TABLE system
        ADD COLUMN(loan_comment varchar(1000) DEFAULT NULL);

To roll back, run the following SQL::

    ALTER TABLE system
        DROP loan_comment;

Add UNIQUE constraint for ``task.name`` (bug :issue:`915549`)
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Run the following SQL::

    DELETE FROM task USING task, task AS vtask
        WHERE task.id < vtask.id AND task.name = vtask.name;
    ALTER TABLE task
        MODIFY name VARCHAR(255) UNIQUE;

The above SQL query will keep the task with the maximum task ID (most
recent one) and remove the others having the same name.

To roll back, run the following SQL::

    ALTER TABLE task
        DROP INDEX name,
        MODIFY name VARCHAR(2048);

Add task result type "None" (bug :issue:`915128`)
+++++++++++++++++++++++++++++++++++++++++++++++++

Run the following SQL::

    ALTER TABLE job
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;
    ALTER TABLE recipe_set
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;
    ALTER TABLE recipe
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;
    ALTER TABLE recipe_task
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;
    ALTER TABLE recipe_task_result
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;

To roll back, run the following SQL::

    ALTER TABLE job
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
    ALTER TABLE recipe_set
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
    ALTER TABLE recipe
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
    ALTER TABLE recipe_task
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
    ALTER TABLE recipe_task_result
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;

Configuration changes
---------------------

Redirect server API documentation
+++++++++++++++++++++++++++++++++

In previous versions, server API documentation was included in the 
beaker-server package and served from ``apidocs/``. It is no longer included in 
the package; it can be browsed on the Beaker web site instead.

Replace the following Alias directive in 
``/etc/httpd/conf.d/beaker-server.conf``::

    Alias /bkr/apidoc /usr/share/bkr/server/apidoc/html

with a Redirect directive (adjust the ``/bkr`` path prefix as appropriate for 
your site)::

    Redirect permanent /bkr/apidoc http://beaker-project.org/docs/server-api

oVirt data center mapping
+++++++++++++++++++++++++

This is only applicable to Beaker sites using oVirt integration.

In previous versions, Beaker looked for usable oVirt data centers by matching 
against the lab controller FQDN (with some modifications to match oVirt naming 
constraints). Now the mapping from lab controllers to oVirt data centers is 
maintained in the Beaker database. This allows you to utilize multiple oVirt 
data centers per lab. See :ref:`ovirt` for details about how to configure the 
mapping.
