
.. _job-monitoring:

Job monitoring
==============

.. todo:: describe beaker-watchdog fully

The :program:`beaker-watchdog` daemon on the lab controller monitors the 
console logs from Conserver (if available) for every running recipe. The 
console log is recorded against the Beaker recipe as a log file named 
``console.log``.

Kernel panic detection
----------------------

The :program:`beaker-watchdog` daemon checks each line of the console log 
against a regexp pattern to find strings which indicate that a kernel panic or 
other fatal kernel error has occurred. When a panic message is found, it is 
recorded as a "Panic" result against the currently running task in the recipe.

Panic detection can be disabled on a per-recipe basis by setting 
``panic="ignore"`` on the ``<watchdog/>`` element in the recipe definition.

Beaker administrators can customize the panic detection pattern for their site 
(see :ref:`customizing-panic`).


Install failure detection
-------------------------

Like the panic detection feature described above, the 
:program:`beaker-watchdog` daemon also checks each line of the console log 
against a set of regexp patterns to find strings which indicate that a fatal 
error occurred during installation. When an installer error message is found, 
the recipe is immediately aborted.

Once the installation has finished, beaker-watchdog ignores any installer error 
messages found in the console log. This is to avoid false positives in case 
some other program prints a message to the console which resembles an installer 
error. Beaker knows when the installation is finished and the execution of 
post-installation scripts has started, as it adds commands that check in with 
the lab controller into the generated kickstart file (see 
:ref:`provisioning-process`).

Install failure detection is controlled by the same mechanism as panic 
detection. It can be disabled on a per-recipe basis by setting 
``panic="ignore"`` on the ``<watchdog/>`` element in the recipe definition.

Beaker administrators can customize the install failure detection patterns for 
their site (see :ref:`customizing-panic`).
