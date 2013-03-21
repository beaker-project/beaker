New system loan interface and comment field
===========================================

System loans are now accessible via an AJAX widget. On top
of the existing functionality, a comment field is availble for
creating comments about current loans. See :ref:`loaning-systems` for
further details.

Run the following SQL::

    ALTER TABLE system ADD COLUMN(loan_comment varchar(1000) DEFAULT NULL);

To roll back, run the following SQL::

    ALTER TABLE system DROP loan_comment;
