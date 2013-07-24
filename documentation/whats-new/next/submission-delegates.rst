Submission delegates (feature)
------------------------------

Submission delegates is a new feature that enables a job to be submitted on
behalf of another user. Once a user has nominated another user to be
a submission delegate, the submission delegate can submit and manage
jobs on behalf of that user. Jobs submitted by the submission delegate
have access to the same system resources that are available to the job
owner, however they only have access to manage jobs they have submitted.

Please run the following SQL::

  ALTER TABLE job ADD COLUMN submitter_id int default NULL,
      ADD CONSTRAINT `job_submitter_id_fk` FOREIGN KEY (`submitter_id`) REFERENCES `tg_user` (`user_id`);

To roll back::

  ALTER TABLE job DROP FOREIGN KEY job_submitter_id_fk,
      DROP submitter_id;

(Contributed by Raymond Mancy :issue:`960302`)
