bkr reads system-wide and user configuration
============================================

The :program:`bkr` client now always loads system-wide configuration from  
:file:`/etc/beaker/client.conf` and per-user configuration from 
:file:`~/.beaker_client/config`. Settings in the per-user configuration file 
override the system-wide configuration. Previously, if the per-user 
configuration file existed, the system-wide configuration would not be loaded.

(Contributed by qhsong and Dan Callaghan in :issue:`844364`.)
