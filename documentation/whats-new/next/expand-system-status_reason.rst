Expand ``system.status_reason``
===============================

Run the following SQL::

    ALTER TABLE system
    MODIFY status_reason VARCHAR(4000);

To roll back, run the following SQL::

    ALTER TABLE system
    MODIFY status_reason VARCHAR(255);
