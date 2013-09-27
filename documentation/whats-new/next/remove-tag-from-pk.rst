Remove ``beaker_tag.tag`` from the table's primary key
======================================================

Run the following SQL::

    ALTER TABLE beaker_tag
        DROP PRIMARY KEY,
        ADD PRIMARY KEY (id);

To roll back, run the following SQL::

    ALTER TABLE beaker_tag
        DROP PRIMARY KEY,
        ADD PRIMARY KEY (id, tag);
