``systemd-readahead`` is disabled on distros which have it
==========================================================

Beaker now disables readahead collection on distros with systemd, in the same 
way that the readahead service is disabled on RHEL6. Readahead is not generally 
useful in Beaker recipes because they typically only boot once, and the harness 
interferes with normal data collection.

You can opt out of this behaviour by setting the ``no_disable_readahead`` 
kickstart metadata variable. This will cause Beaker to omit the snippet which 
disables readahead collection.
