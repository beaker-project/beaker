Add task result type "None"
===========================

Run the following SQL::

    ALTER TABLE job
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;
    ALTER TABLE recipe_set
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;
    ALTER TABLE recipe
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;
    ALTER TABLE recipe_task
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;
    ALTER TABLE recipe_task_result
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic', 'None') NOT NULL;

To roll back, run the following SQL::

    ALTER TABLE job
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
    ALTER TABLE recipe_set
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
    ALTER TABLE recipe
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
    ALTER TABLE recipe_task
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
    ALTER TABLE recipe_task_result
        MODIFY result ENUM('New', 'Pass', 'Warn', 'Fail', 'Panic') NOT NULL;
