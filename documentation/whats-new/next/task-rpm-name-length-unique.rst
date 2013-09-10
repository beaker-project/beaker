Task RPM filename is UNIQUE and limited to 255 characters
=========================================================

An unique constraint is now enforced on the Task RPM names and they
are restricted to a maximum of 255 characters in length. It is worth
noting that this restriction was already in place, albeit implicitly:

   - The RPM name could not be more than 255 characters due to the
     filesystem restrictions

   - Duplicate filenames could not be uploaded due to a check during
     upload in Beaker

Hence, this change merely makes the data model consistent with the
reality.

To update the ``task`` table with the ``UNIQUE`` constraint on
``rpm``, run the following SQL::

    ALTER TABLE task
	MODIFY rpm VARCHAR(255) UNIQUE;

For rollback, run the following SQL::

    ALTER TABLE task
	DROP INDEX rpm;

    ALTER TABLE task
	MODIFY rpm VARCHAR(2048);
