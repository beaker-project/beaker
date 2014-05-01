Record job activities
===========================

Database changes
----------------

Run ``beaker-init`` to create the new tables.

To roll back, drop the newly created tables::

    DROP TABLE job_activity;
