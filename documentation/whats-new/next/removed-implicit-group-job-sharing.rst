Removed "implicit group job sharing" behaviour
==============================================

This release removes support for Beaker's original group sharing model for 
jobs, which allowed any group member to have full control over any jobs 
submitted by any other members of the group. This "implicit job sharing" 
behaviour was deprecated in Beaker 0.15 and disabled by default in Beaker 22.

In previous releases the ``beaker.deprecated_job_group_permissions.on`` setting 
could be used to enable the old, deprecated behaviour. This setting is now 
ignored.
