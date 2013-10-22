Upgrading to Beaker 0.15
========================

Configuration changes
---------------------

Static web assets served from /assets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beaker 0.15 uses a new URL prefix for static web assets, ``/assets``. To
ensure assets are served correctly, add the following configuration to
``/etc/httpd/conf.d/beaker-server.conf``. Adjust the ``/bkr`` prefix as
appropriate for your installation.

::

    Alias /bkr/assets /usr/share/bkr/server/assets

    # Generated assets have a content hash in their filename so they can
    # safely be cached forever.
    <Directory /usr/share/bkr/server/assets/generated>
        ExpiresActive on
        ExpiresDefault "access plus 1 year"
    </Directory>


Database changes
----------------

After upgrading the ``beaker-server`` package on your Beaker server please run
the additional database upgrade instructions below.


System access policies changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. important:: In the original release of Beaker 0.15.0 these upgrade instructions did not 
   create all necessary access policy rules (see :issue:`1015328`). The amended 
   SQL statements appear below.
   
   If you previously followed the upgrade instructions for Beaker 0.15.0, run 
   the SQL statements again to ensure all necessary rules are created.

Run ``beaker-init`` to create the new tables. Then run the following SQL to
populate them based on the Shared and Group configuration of existing systems::

    INSERT INTO system_access_policy (system_id)
    SELECT id FROM system
    WHERE NOT EXISTS (SELECT 1 FROM system_access_policy
        WHERE system_id = system.id);

    INSERT INTO system_access_policy_rule
        (policy_id, user_id, group_id, permission)
    SELECT system_access_policy.id, NULL, NULL, 'control_system'
    FROM system_access_policy
    INNER JOIN system ON system_access_policy.system_id = system.id
    WHERE NOT EXISTS (SELECT 1 FROM system_access_policy_rule
        WHERE policy_id = system_access_policy.id
            AND user_id IS NULL
            AND group_id IS NULL
            AND permission = 'control_system');

    INSERT INTO system_access_policy_rule
        (policy_id, user_id, group_id, permission)
    SELECT system_access_policy.id, NULL, NULL, 'reserve'
    FROM system_access_policy
    INNER JOIN system ON system_access_policy.system_id = system.id
    WHERE shared = TRUE
        AND NOT EXISTS (SELECT 1 FROM system_group
            WHERE system_id = system.id)
        AND NOT EXISTS (SELECT 1 FROM system_access_policy_rule
            WHERE policy_id = system_access_policy.id
                AND user_id IS NULL
                AND group_id IS NULL
                AND permission = 'reserve');

    INSERT INTO system_access_policy_rule
        (policy_id, user_id, group_id, permission)
    SELECT system_access_policy.id, NULL, system_group.group_id, 'reserve'
    FROM system_access_policy
    INNER JOIN system ON system_access_policy.system_id = system.id
    INNER JOIN system_group ON system_group.system_id = system.id
    WHERE shared = TRUE
        AND system_group.admin = FALSE
        AND NOT EXISTS (SELECT 1 FROM system_access_policy_rule
            WHERE policy_id = system_access_policy.id
                AND user_id IS NULL
                AND group_id = system_group.group_id
                AND permission = 'reserve');

    INSERT INTO system_access_policy_rule
        (policy_id, user_id, group_id, permission)
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
    WHERE system_group.admin = TRUE
        AND NOT EXISTS (SELECT 1 FROM system_access_policy_rule
            WHERE policy_id = system_access_policy.id
                AND user_id IS NULL
                AND group_id = system_group.group_id
                AND permission = permission.p);

To roll back, drop the newly created tables::

    DROP TABLE system_access_policy_rule;
    DROP TABLE system_access_policy;

Once you are satisfied that the upgrade is successful, you can drop the
obsoleted columns. There is no rollback procedure for this step.

::

    ALTER TABLE system DROP shared;
    ALTER TABLE system_group DROP admin;


Drop tables for TurboGears Visit framework
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As part of the migration to Flask, Beaker no longer uses the TurboGears
Visit framework

Run the following SQL::

    DROP TABLE visit;
    DROP TABLE visit_identity;

To roll back, downgrade Beaker and then run the ``beaker-init`` command to
re-create the tables.


Group name and display name changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The maximum group name length has now been increased to 255 characters
from 16 characters.

Please run the following SQL::

    ALTER TABLE tg_group MODIFY group_name VARCHAR(255);

To rollback::

    ALTER TABLE tg_group MODIFY group_name VARCHAR(16);


Task RPM filename is UNIQUE and limited to 255 characters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An unique constraint is now enforced on the Task RPM names and they
are restricted to a maximum of 255 characters in length. It is worth
noting that this restriction was already in place, albeit implicitly:

- The RPM name could not be more than 255 characters due to the
  filesystem restrictions

- Duplicate filenames could not be uploaded due to a check during
  upload in Beaker

Hence, this change merely makes the data model consistent with the
reality.

To update the ``task`` table with the ``UNIQUE`` constraint on
``rpm``, run the following SQL::

    ALTER TABLE task
        MODIFY rpm VARCHAR(255) UNIQUE;

For rollback, run the following SQL::

    ALTER TABLE task
        DROP INDEX rpm;

    ALTER TABLE task
        MODIFY rpm VARCHAR(2048);

