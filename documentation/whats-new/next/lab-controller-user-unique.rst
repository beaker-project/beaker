Lab controller user accounts required to be unique
==================================================

Beaker now correctly prevents multiple lab controllers from being associated 
with a single user account.

Run the following SQL::

    ALTER TABLE lab_controller ADD UNIQUE KEY uc_user_id (user_id);

To roll back, run the following SQL::

    ALTER TABLE lab_controller DROP KEY uc_user_id;
