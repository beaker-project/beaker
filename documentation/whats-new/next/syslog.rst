Beaker daemons log to syslog
============================

The beakerd daemon, the lab controller daemons, and the Beaker web application 
running in Apache now all send their log messages to syslog, rather than 
writing to files in ``/var/log/beaker`` directly.

Due to a TurboGears limitation you *must* remove the ``[logging]`` section from 
``/etc/beaker/server.cfg`` *before* upgrading the ``beaker-server`` package, 
since the settings in that section conflict with the syslog-based 
configuration.

Logging options in ``/etc/beaker/labcontroller.conf`` will be ignored if 
present, and can be removed if desired.

Beaker's log file locations and log rotation settings are now configured 
through the standard system mechanisms: ``/etc/rsyslog.d`` and 
``/etc/logrotate.d``. If you had customised Beaker's logging configuration 
previously, you should make the same modifications to the new configuration 
files.
