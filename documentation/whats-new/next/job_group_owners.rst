Job group owner ("feature")
===============

This change allows specifying a group owner of a job. This is done via the
``group`` attribute on a job XML's ``&lt;job /&gt;``, or by passing
the ``--job-group`` option to a client workflow command. The group owners
will have the same permissions for viewing/modifying a job as the original
submitter. (Contributed by Raymond Mancy in :issue:`908183`.)

Database Changes
----------------
Please run the following:

  ALTER TABLE job
      ADD COLUMN group_id int(11) default NULL AFTER owner_id,
      ADD CONSTRAINT `job_group_id_fk` FOREIGN KEY (group_id)
          REFERENCES `tg_group` (group_id);


To roll back:

  ALTER TABLE job DROP FOREIGN KEY job_group_id_fk, DROP COLUMN group_id;
