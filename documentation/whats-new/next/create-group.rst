Create user group ("feature")
=============================

Beaker users can now create user groups without having admin
privileges. A new sub-command ``bkr group-create`` is added to create a group from
the command line, in addition to the Web UI. (Contributed by Amit Saha
in :issue:`908172`.)

Database Changes
----------------
Please run the following:

    ALTER TABLE user_group
        ADD is_owner BOOLEAN DEFAULT FALSE;

To roll back:

   ALTER TABLE user_group
       DROP COLUMN is_owner;
