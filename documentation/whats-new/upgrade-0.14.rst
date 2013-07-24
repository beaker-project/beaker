Upgrading to Beaker 0.14
========================

Configuration changes
---------------------

Beaker daemons logging to syslog
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The beakerd daemon, the lab controller daemons, and the Beaker web
application running in Apache now all send their log messages to syslog,
rather than writing to files in ``/var/log/beaker`` directly.

Due to a TurboGears limitation you *must* remove the ``[logging]`` section
from ``/etc/beaker/server.cfg`` *before* upgrading the ``beaker-server``
package, since the settings in that section conflict with the syslog-based
configuration.

Logging options in ``/etc/beaker/labcontroller.conf`` will be ignored if
present, and can be removed if desired.

Beaker's log file locations and log rotation settings are now configured
through the standard system mechanisms: ``/etc/rsyslog.d`` and
``/etc/logrotate.d``. If you had customised Beaker's logging configuration
previously, you should make the same modifications to the new configuration
files.


Database changes
----------------

After upgrading the ``beaker-server`` package on your Beaker server please run
the additional database upgrade instructions below.


Submission delegates changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``beaker-init`` to add the new ``submission_delegate`` table.

Run the following SQL to add the submitter attribute to jobs::

  ALTER TABLE job ADD COLUMN submitter_id int default NULL,
      ADD CONSTRAINT `job_submitter_id_fk` FOREIGN KEY (`submitter_id`) REFERENCES `tg_user` (`user_id`);

To roll back::

  ALTER TABLE job DROP FOREIGN KEY job_submitter_id_fk,
      DROP submitter_id;
  DROP TABLE submission_delegate;
