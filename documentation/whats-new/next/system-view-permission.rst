"View" permission in system access policies
===========================================

System access policies have a new permission, "view", which controls who can 
see the system in Beaker's inventory. This replaces the previous "Secret" flag 
for systems giving finer grained control over visibility. The default for new 
systems is to grant "view" permission to everybody.

Database changes
----------------

To add the new "view" permission, run the following SQL::

    ALTER TABLE system_access_policy_rule
    MODIFY permission ENUM('edit_policy', 'edit_system', 'loan_any',
            'loan_self', 'control_system', 'reserve', 'view');

The following SQL will populate the access policies with a rule granting 
everybody "view" permission for existing systems that are not marked secret.

::

    INSERT INTO system_access_policy (system_id)
    SELECT id FROM system
    WHERE NOT EXISTS (SELECT 1 FROM system_access_policy
        WHERE system_id = system.id);

    INSERT INTO system_access_policy_rule
        (policy_id, user_id, group_id, permission)
    SELECT system_access_policy.id, NULL, NULL, 'view'
    FROM system_access_policy
    INNER JOIN system ON system_access_policy.system_id = system.id
    WHERE NOT EXISTS (SELECT 1 FROM system_access_policy_rule
        WHERE policy_id = system_access_policy.id
            AND user_id IS NULL
            AND group_id IS NULL
            AND permission = 'view')
        AND system.private = 0;

To roll back, delete the newly created rules and adjust the permission enum::

    DELETE FROM system_access_policy_rule
    WHERE permission = 'view';

    ALTER TABLE system_access_policy_rule
    MODIFY permission ENUM('edit_policy', 'edit_system', 'loan_any',
            'loan_self', 'control_system', 'reserve');

Once you are satisfied that the upgrade is successful, you can drop the
obsoleted column. There is no rollback procedure for this step.

::

    ALTER TABLE system DROP private;
