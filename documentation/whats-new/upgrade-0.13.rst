Upgrading to Beaker 0.13
========================

Database changes
----------------

After upgrading the ``beaker-server`` package on your Beaker server, follow
the additional database upgrade instructions below.


Enhanced user group changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the following SQL::

    ALTER TABLE tg_group
        MODIFY group_name VARCHAR(16) NOT NULL,
        ADD COLUMN ldap BOOLEAN NOT NULL DEFAULT 0,
        ADD INDEX (ldap),
        ADD COLUMN root_password VARCHAR(255) AFTER display_name;

    ALTER TABLE user_group
        ADD is_owner BOOLEAN DEFAULT FALSE;

    ALTER TABLE job
        ADD COLUMN group_id int(11) default NULL AFTER owner_id,
        ADD CONSTRAINT `job_group_id_fk` FOREIGN KEY (group_id)
            REFERENCES `tg_group` (group_id);

To roll back, run the following SQL::

    ALTER TABLE tg_group
        MODIFY group_name VARCHAR(16) DEFAULT NULL,
        DROP COLUMN ldap,
        DROP COLUMN root_password;

    ALTER TABLE user_group
        DROP COLUMN is_owner;

    ALTER TABLE job
        DROP FOREIGN KEY job_group_id_fk, DROP COLUMN group_id;

Add explicit indices for frequently searched columns
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the following SQL::

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

To roll back, run the following SQL::

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


Delete duplicate system_status_duration rows with NULL finish_time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the following SQL::

    DELETE FROM system_status_duration
    USING system_status_duration
    LEFT JOIN (
        SELECT system_id, MAX(start_time) start_time
        FROM system_status_duration
        GROUP BY system_id) x
        ON system_status_duration.system_id = x.system_id
            AND system_status_duration.start_time = x.start_time
    WHERE finish_time IS NULL
        AND x.start_time IS NULL;

This will clear out any lingering remnants of bug :issue:`903902`.


Other changes
-------------

Re-import distro trees
~~~~~~~~~~~~~~~~~~~~~~~

As ``beaker-distro-import`` now correctly imports the ``optional-debuginfo``
repository (where it is available), it may be desirable to re-import all
distro trees. The exact mechanism for doing so will depend on how the
particular Beaker installation triggers distro imports.
