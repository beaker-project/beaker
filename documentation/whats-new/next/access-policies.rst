Access policies for systems
===========================

Access policies are a new, more flexible mechanism for controlling who can 
access a Beaker system. Access policies replace the existing access controls 
for systems, based on the :guilabel:`Shared` flag and the system's group 
memberships.

In earlier Beaker releases, any logged-in user was permitted to power any 
system. This permission is preserved in the access policy for existing systems 
when migrating to this release. However, system owners can now remove this rule 
from their system's access policy if desired.

The restriction preventing unprivileged users from sharing their system with 
all Beaker users has been removed.

Database changes
----------------

Run ``beaker-init`` to create the new tables. Then run the following SQL to 
populate them based on the Shared and Group configuration of existing systems::

    INSERT INTO system_access_policy (system_id)
    SELECT id FROM system;

    INSERT INTO system_access_policy_rule (policy_id, user_id, group_id, permission)
    SELECT system_access_policy.id, NULL, NULL, 'control_system'
    FROM system_access_policy
    INNER JOIN system ON system_access_policy.system_id = system.id;

    INSERT INTO system_access_policy_rule (policy_id, user_id, group_id, permission)
    SELECT system_access_policy.id, NULL, NULL, 'reserve'
    FROM system_access_policy
    INNER JOIN system ON system_access_policy.system_id = system.id
    WHERE shared = TRUE AND
        NOT EXISTS (SELECT 1 FROM system_group WHERE system_id = system.id);

    INSERT INTO system_access_policy_rule (policy_id, user_id, group_id, permission)
    SELECT system_access_policy.id, NULL, system_group.group_id, permission.p
    FROM system_access_policy
    INNER JOIN system ON system_access_policy.system_id = system.id
    INNER JOIN system_group ON system_group.system_id = system.id
    JOIN (SELECT 'edit_policy' p
        UNION SELECT 'edit_system' p
        UNION SELECT 'loan_any' p
        UNION SELECT 'loan_self' p
        UNION SELECT 'control_system' p
        UNION SELECT 'reserve' p) permission
    WHERE shared = TRUE AND system_group.admin = TRUE;

To roll back, drop the newly created tables::

    DROP TABLE system_access_policy_rule;
    DROP TABLE system_access_policy;

Once you are satisfied that the upgrade is successful, you can drop the 
obsoleted columns. There is no rollback procedure for this step.

::

    ALTER TABLE system DROP shared;
    ALTER TABLE system_group DROP admin;
