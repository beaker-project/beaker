``system.release_action`` column is not NULLable
================================================

To avoid duplication across the code, we now always store a release action in 
the database. The default is ``PowerOff`` to match the existing behaviour.

Before making any changes to the schema, we should gather a list of systems
that will be updated, in case we need to roll back::

    SELECT GROUP_CONCAT(fqdn) FROM system WHERE release_action IS NULL;

Save the output in case of rollback.

The following changes are needed to be made to the schema::

    UPDATE system SET release_action = 'PowerOff' WHERE release_action IS NULL;
    ALTER TABLE system MODIFY COLUMN release_action enum('PowerOff','LeaveOn','ReProvision') NOT NULL;

To roll back::

    ALTER TABLE system MODIFY COLUMN release_action enum('PowerOff','LeaveOn','ReProvision') DEFAULT NULL;
    UPDATE system SET release_action = NULL WHERE system.fqdn IN (<list from previous query>);
