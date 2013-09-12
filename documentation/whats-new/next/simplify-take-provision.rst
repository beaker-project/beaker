Simplified "Take", "Schedule Provision", and "Provision Now" in the web UI
==========================================================================

The :guilabel:`Take` and :guilabel:`Return` buttons on the system page no 
longer appear for systems set to Automated, as this was a common source of 
confusion for new users. To temporarily give a user exclusive access to run 
scheduled jobs on a system, loan it to them. If a system owner needs to reserve 
a system directly, bypassing the scheduler, they should first set the system to 
Manual.

The :guilabel:`Provision` tab on the system page now always schedules a new job 
for Automated systems, and always provisions immediately for Manual systems, 
instead of varying its behaviour according to a complicated set of rules.

Contributed by Dan Callaghan in :issue:`855333`.
