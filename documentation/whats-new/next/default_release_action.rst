Update system table to include default release action
=====================================================
To avoid duplication across the code, we now rely on the database to set
the default release action.

Before making any changes to the schema, we should gather a list of systems
that will be updated, in case we need to roll back::

    SELECT GROUP_CONCAT(fqdn) FROM system WHERE release_action IS NULL;

Save the output in case of rollback.

The following changes are needed to be made to the schema::

    UPDATE system SET release_action = 'PowerOff' WHERE release_action IS NULL;
    ALTER TABLE system MODIFY COLUMN release_action enum('PowerOff','LeaveOn','ReProvision') DEFAULT 'PowerOff' NOT NULL;

To roll back::

    UPDATE system SET release_action = NULL WHERE system.fqdn IN (<list from previous query>);
    ALTER TABLE system MODIFY COLUMN release_action enum('PowerOff','LeaveOn','ReProvision') DEFAULT NULL;


