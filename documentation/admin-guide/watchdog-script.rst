Customizing expired watchdog handling
=====================================

When the watchdog timer for a recipe expires, by default the 
:program:`beaker-watchdog` daemon aborts the recipe.

You can supply a custom script to handle watchdog expiry by setting 
``WATCHDOG_SCRIPT`` in :file:`/etc/beaker/labcontroller.conf`. If this option 
is set, :program:`beaker-watchdog` invokes the named script to handle the 
watchdog expiry instead.

The watchdog script is executed with three arguments: the system FQDN, the 
recipe ID, and the currently running task ID. If the script wants to handle the 
watchdog expiry (for example, by triggering a crash dump to network storage) it 
should print to stdout the number of seconds to extend the watchdog timer by, 
and then exit with zero status. A non-zero exit status from the script is 
interpreted as failure and :program:`beaker-watchdog` will abort the recipe as 
usual in that case.

Note that if the script requests an extension to the watchdog, it will be 
invoked again if the recipe is still not finished when the newly extended 
watchdog time is next reached. Therefore, to avoid infinite watchdog extension, 
the script must either take care to avoid handling the same recipe ID multiple 
times, or it must abort the recipe using some external mechanism after exiting.
