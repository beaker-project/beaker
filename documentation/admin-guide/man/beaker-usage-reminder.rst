beaker-usage-reminder: Send Beaker usage reminder
=================================================

.. program:: beaker-usage-reminder

Synopsis
--------

| :program:`beaker-usage-reminder` [*options*]

Description
-----------

``beaker-usage-reminder`` is used to send users email reminders and allow
them to keep track of their Beaker systems usage.

To ensure users get their reminders, beaker administrators can setup a cron
job on the beaker server to run this command at regular intervals (e.g. daily).

Options
-------

.. option:: --reservation-expiry <reservation-expiry>

   Warn users about their reservations expiring in <hours> hours.

.. option:: --reservation-length <reservation-length> , --waiting-recipe-age <waiting-recipe-age>

   Report users about their systems which have been reserved for longer than <days> days and there
   is at least one recipe waiting for longer than <hours> hours for those systems.

.. option:: --delayed-job-age <delayed-job-age>

   Warn users about their jobs which have been queued for longer than <days> days.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

To remind users who have expiring reservations in 48 hours::

    beaker-usage-reminder --reservation-expiry 48

To remind users who have systems that have been reserved for longer
than 3 days and there is at least one recipe waiting for longer than
1 hour for those systems::

    beaker-usage-reminder --reservation-length 3 --waiting-recipe-age 1

To remind users who have delayed jobs for longer than 3 days::

    beaker-usage-reminder --delayed-job-age 3
