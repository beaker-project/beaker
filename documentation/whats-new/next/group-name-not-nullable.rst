Database changes
----------------

Run the following SQL:

    ALTER TABLE tg_group
        MODIFY group_name VARCHAR(16) NOT NULL;

To roll back, run the following SQL:

    ALTER TABLE tg_group
        MODIFY group_name VARCHAR(16) DEFAULT NULL;
