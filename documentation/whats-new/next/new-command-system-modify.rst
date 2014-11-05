bkr system-modify
=================

A new command, ``system-modify`` has been added to the beaker client
to modify attributes of existing systems. This release adds the ability to 
change the system owner and condition.

Example::

    bkr system-modify --owner jdoe mysystem.test.fqdn

(Contributed by Amit Saha and Dan Callaghan in :issue:`1118884`, 
:issue:`804479`)
