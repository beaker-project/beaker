Broken system detection
=======================

.. todo::
   Find a better top-level heading for this to live under

The Beaker scheduler includes some heuristics to automatically set a system's 
condition to Broken if the system appears to be unable to successfully run 
recipes. The system owner is notified by email so that they can take 
corrective action before setting the system's condition back to Automated.

The feature is intended to prevent a misconfigured or faulty system from 
ruining a large number of jobs if the system owner isn't able to immediately 
correct the problem or remove the system from service. However, the heuristics 
used are very conservative, to avoid false positives caused by a distro bug or 
a mistake in a Beaker task.

Beaker will set a system's condition to Broken under the following 
circumstances:

* when a power command for the system fails

  Failed power commands are usually caused by incorrect power settings, 
  connectivity problems, or a faulty management controller. In any case, if the 
  system cannot be powered then it cannot execute recipes, so in this case it 
  is always marked broken immediately.

* when two consecutive recipes running on the system, using two different
  "reliable" distros, are aborted by the external watchdog

  A distro is considered "reliable" if it is tagged with the tag given in the 
  ``beaker.reliable_distro_tag`` config setting. The suggested tag is 
  ``RELEASED``. If the ``beaker.reliable_distro_tag`` setting is unset, this 
  heuristic is not used.

  Note that the two distros must be different in order to trigger this 
  heuristic. This is to reduce the chance that the abort was caused by a distro 
  bug rather than a problem with the system.
