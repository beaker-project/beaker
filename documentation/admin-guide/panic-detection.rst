
.. _customizing-panic:

Customizing panic detection and install failure detection
=========================================================

The :program:`beaker-watchdog` daemon on the lab controller scans console logs 
to detect if a recipe has triggered a kernel panic, or if the installation has 
failed with a fatal error.

You can customize the regexp pattern for detecting kernel panics by setting 
``PANIC_REGEX`` in ``/etc/beaker/labcontroller.conf``. The default pattern that 
ships with Beaker is defined in 
``/usr/lib/python2.7/site-packages/bkr/labcontroller/default.conf``. The
pattern uses :ref:`Python regular expression syntax <python:re-syntax>`.

Install failure patterns are read from a directory (rather than using a single 
pattern like the panic detection). Each file contains a regexp pattern which is 
checked against the console log. If any pattern matches, the installation is 
considered to have failed.

Beaker ships a number of default patterns in the 
``/usr/lib/python2.7/site-packages/bkr/labcontroller/install-failure-patterns/``
directory. You can define extra custom patterns by placing them in 
``/etc/beaker/install-failure-patterns/``. A custom pattern overrides a default 
pattern with the same filename. If a pattern is empty, Beaker ignores it. If 
you want to disable a default pattern, create an empty file with the same name 
in ``/etc/beaker/install-failure-patterns/``.
