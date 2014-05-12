User e-mail addresses no longer required to be unique
=====================================================

Beaker no longer enforces uniqueness for user e-mail addresses.

Run the following SQL::

    ALTER TABLE tg_user
        DROP KEY email_address,
        ADD INDEX email_address (email_address);

To roll back, run the following SQL. If duplicate e-mail addresses have since 
been entered, you must first manually correct them.

::

    ALTER TABLE tg_user
        DROP INDEX email_address,
        ADD UNIQUE email_address (email_address);
