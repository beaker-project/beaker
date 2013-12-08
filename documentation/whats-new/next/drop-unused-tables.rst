Drop unused tables
==================

Some tables have existed in Beaker's database schema since its inception but 
were never used and do not contain any data. Run the following SQL to drop 
these tables::

    DROP TABLE locked;
    DROP TABLE serial;
    DROP TABLE serial_type;
    DROP TABLE install;

To roll back, downgrade the ``beaker-server`` package to the previous version 
and then run ``beaker-init`` to create the dropped tables.
