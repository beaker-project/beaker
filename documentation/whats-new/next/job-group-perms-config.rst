Config option for job group permissions (breakage)
==================================================

The implicit permission given to group co-members over jobs
is now enabled via an entry in Beaker's configuration file:

  beaker.deprecated_job_group_permissions.on = True

In the absence of the configuration entry, it defaults
to 'False'.

(Contributed by Raymond Mancy in :issue:`1000861`)
