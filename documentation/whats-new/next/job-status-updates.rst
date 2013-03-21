Job status is updated asynchronously
====================================

The beakerd daemon is now responsible for updating job status based on the 
latest state of the tasks in the job. This includes sending notifications and 
returning systems when a recipe finishes.

This change increases throughput for task status updates made by the harness 
while running a recipe, and eliminates various race conditions which can leave 
jobs or systems in an inconsistent state (see bugs :issue:`807237` and 
:issue:`715226` for details).

However, the job and recipe states shown in Beaker's interface (including 
Status, Result, and progress bars) will lag a small amount behind reality. The 
amount of lag is expected to be less than 20 seconds (the polling interval for 
beakerd).

Database changes
----------------

Run the following SQL::

    ALTER TABLE job
        ADD COLUMN dirty_version BINARY(16) NOT NULL AFTER id,
        ADD COLUMN clean_version BINARY(16) NOT NULL AFTER dirty_version,
        ADD INDEX ix_job_dirty_clean_version (dirty_version, clean_version);
    UPDATE job SET dirty_version = '1111111111111111';

To roll back, run the following SQL::

    ALTER TABLE job
        DROP COLUMN dirty_version,
        DROP COLUMN clean_version;
