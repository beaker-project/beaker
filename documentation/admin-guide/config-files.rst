Configuration files
===================

The following configuration files are used by Beaker. Each setting in the 
configuration file has an explanatory comment, and the default value for the 
setting is shown commented out.

:file:`/etc/beaker/server.cfg`
------------------------------

This is the main configuration file for beakerd and the web application, 
including database connection settings.

.. literalinclude:: ../../Server/server.cfg
   :language: ini

:file:`/etc/beaker/labcontroller.conf`
--------------------------------------

The main configuration file for the lab controller daemons.

.. literalinclude:: ../../LabController/labcontroller.conf

Other configuration files installed by Beaker
---------------------------------------------

The following configuration files are also installed by Beaker. The defaults 
provided by these files are suitable for most deployments, but you can tweak 
these settings if desired.

:file:`/etc/httpd/conf.d/beaker-server.conf`
    Apache configuration for serving the web application. You can modify this 
    if you need to adjust authentication or mod_wsgi settings, or if you want 
    to serve the web application at a path other than the default (``/bkr/``).

:file:`/etc/httpd/conf.d/beaker-lab-controller.conf`
    Apache configuration for serving job logs cached on the lab controller.

:file:`/etc/cron.d/beaker`, :file:`/etc/cron.hourly/beaker_expire_distros`
    Scheduled jobs which are required for Beaker's operation.

:file:`/etc/rsyslog.d/beaker-server.conf`, :file:`/etc/rsyslog.d/beaker-lab-controller.conf`
    Configuration for rsyslog to send Beaker log messages to the relevant files 
    in :file:`/var/log/beaker`.

:file:`/etc/logrotate.d/beaker`
    Configuration for logrotate to rotate log files in :file:`/var/log/beaker`.

:file:`/etc/sudoers.d/beaker_proxy_clear_netboot`
    Configuration for sudo to grant beaker-proxy heightened privileges to clear 
    netboot configuration in :file:`/var/lib/tftpboot`.
