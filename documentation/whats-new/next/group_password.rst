Group password (feature)
========================

Group owners can set a root password for their group. The password is used as 
the root password on systems provisioned for a group job.

Run the following SQL::

    ALTER TABLE tg_group
        ADD COLUMN root_password VARCHAR(255) AFTER display_name;

To rollback::

    ALTER TABLE tg_group
        DROP COLUMN root_password;
