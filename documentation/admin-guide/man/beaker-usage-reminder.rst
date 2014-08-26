.. _beaker-usage-reminder:

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

This command requires read access to the Beaker server configuration. Run it as 
root or as another user with read access to the configuration file.

Options
-------

.. option:: --reservation-expiry <hours>

   Warn users about their reservations expiring less than <hours> in the 
   future. The default is 24.

.. option:: --reservation-length <days>, --waiting-recipe-age <hours>

   Remind users about their systems which have been reserved for longer than 
   <days> and there is at least one recipe waiting for longer than <hours> for 
   those systems. The defaults are 3 and 1 respectively.

.. option:: --delayed-job-age <days>

   Warn users about their jobs which have been queued for longer than <days>. 
   The default is 14.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

To remind users who have reservations expiring in 48 hours::

    beaker-usage-reminder --reservation-expiry 48

To remind users who have systems that have been reserved for longer
than 3 days and there is at least one recipe waiting for longer than
1 hour for those systems::

    beaker-usage-reminder --reservation-length 3 --waiting-recipe-age 1

To remind users who have delayed jobs for longer than 3 days::

    beaker-usage-reminder --delayed-job-age 3
