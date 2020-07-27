
.. _customizing-power-commands:

Customizing power commands
==========================

When executing a power command (for example, rebooting a system) the
Beaker lab controller looks for an executable script named after the
system’s power type (for example, ``ipmitool``). The following
directories are searched on the lab controller, in order:

-  ``/etc/beaker/power-scripts``

   Custom power scripts may be placed here.

-  ``/usr/lib/python2.7/site-packages/bkr/labcontroller/power-scripts``

   These templates are packaged with Beaker and should not be modified.

When a script is found it is executed with the following environment
variables set according to the system’s power settings in Beaker:

-  *power\_address*

-  *power\_id*

-  *power\_user*

-  *power\_pass*

Additionally, the power\_mode environment variable will be set to either
``on`` or ``off``, depending on the power action.
