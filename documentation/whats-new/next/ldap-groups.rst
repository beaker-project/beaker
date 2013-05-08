LDAP groups
===========

Beaker now supports populating group membership from an LDAP directory.

Database changes
----------------

Run the following SQL:

    ALTER TABLE tg_group
        ADD COLUMN ldap BOOLEAN NOT NULL DEFAULT 0,
        ADD INDEX (ldap);

To roll back, run the following SQL:

    ALTER TABLE tg_group
        DROP COLUMN ldap;
