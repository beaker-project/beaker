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

* when there is a run of suspicious aborted recipes

  A recipe is considered "suspicious" (that is, indicating the system might be
  broken) if all tasks in the recipe are aborted.

  It is considered to be a "run" if there has been two or more consecutive
  suspicious recipes, with no intervening non-suspicious recipes and no manual
  changes made to the system's status.

  To reduce the risk of false positives, this heuristic is only applied when the
  aborted recipes used a "reliable" distro. A distro is considered reliable if
  it is tagged with the tag given in the ``beaker.reliable_distro_tag`` config
  setting. The suggested tag is ``RELEASED``. If the
  ``beaker.reliable_distro_tag`` setting is unset, this heuristic is not used.

  The run of suspicious recipes must also use at least two different distros in
  order to trigger this heuristic. This is to reduce the chance that the aborted
  was caused by a distro bug rather than a problem with the system.
