UNIQUE constraint for ``system.fqdn`` column
============================================

Run the following SQL::

    ALTER TABLE system
        ADD UNIQUE (fqdn);

To roll back, run the following SQL::

    ALTER TABLE system
        DROP INDEX fqdn;
