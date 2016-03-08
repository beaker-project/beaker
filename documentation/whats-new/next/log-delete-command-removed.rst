Deprecated ``log-delete`` command alias is removed
==================================================

In Beaker 0.15, the :program:`log-delete` server utility was renamed to 
:program:`beaker-log-delete` to better reflect its purpose and reduce the 
chance of conflicts. The original :program:`log-delete` command was retained as 
a deprecated compatibility alias.

In this release, the compatibility alias has been dropped. Beaker 
administrators should ensure that any cron jobs or other scripts have been 
updated to use the correct command, :program:`beaker-log-delete`.
