New ``view_power`` permission for systems
=========================================

.. todo:: put this into alembic once that is merged

Run the following SQL::

    ALTER TABLE system_access_policy_rule
    MODIFY permission ENUM('edit_policy', 'edit_system', 'loan_any',
        'loan_self', 'control_system', 'reserve', 'view', 'view_power')
        NOT NULL;

To roll back, run the following SQL::

    DELETE FROM system_access_policy_rule 
    WHERE permission='view_power';

    ALTER TABLE system_access_policy_rule
    MODIFY permission ENUM('edit_policy', 'edit_system', 'loan_any',
        'loan_self', 'control_system', 'reserve', 'view')
        DEFAULT NULL;
