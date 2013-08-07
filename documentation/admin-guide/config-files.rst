Configuration files
===================

The following configuration files are used by Beaker.

``/etc/beaker/server.cfg``
    Main configuration file for beakerd and the web application, including 
    database connection settings. Refer to the comments in this file for 
    details about the available options.

``/etc/beaker/labcontroller.conf``
    Main configuration file for the lab controller daemons. Refer to the 
    comments in this file for details about the available options.

``/etc/httpd/conf.d/beaker-server.conf``
    Apache configuration for serving the web application. You can modify this 
    if you need to adjust authentication or mod_wsgi settings, or if you want 
    to serve the web application at a path other than the default (``/bkr/``).

``/etc/httpd/conf.d/beaker-lab-controller.conf``
    Apache configuration for serving job logs cached on the lab controller.

``/etc/cron.d/beaker``, ``/etc/cron.hourly/beaker_expire_distros``
    Scheduled jobs which are required for Beaker's operation.

``/etc/rsyslog.d/beaker-server.conf``,  ``/etc/rsyslog.d/beaker-lab-controller.conf``
    Configuration for rsyslog to send Beaker log messages to the relevant files 
    in ``/var/log/beaker``.

``/etc/logrotate.d/beaker``
    Configuration for logrotate to rotate log files in ``/var/log/beaker``.

``/etc/sudoers.d/beaker_proxy_clear_netboot``
    Configuration for sudo to grant beaker-proxy heightened privileges to clear 
    netboot configuration in ``/var/lib/tftpboot``.
