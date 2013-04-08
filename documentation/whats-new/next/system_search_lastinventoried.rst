System search using inventory date and status
=============================================

It is now possible to search for systems from the Beaker Web UI (See
:ref:`system-searching`) based on the date on which they were last
inventoried on.

This can be (ab)used to check the inventory status of the
systems. Searching for systems using the "is" operator with a blank
date value returns all uninventoried systems, where as using the "is
not" operator will return all inventoried systems.



(Contributed by Amit Saha in :issue:`949777`.)
