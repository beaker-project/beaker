Logs are no longer sent to the Beaker server
============================================

Originally the beaker-proxy daemon forwarded log chunks from the test systems 
to the Beaker server for storage. During the 0.5.x series, the beaker-transfer 
daemon was added, to optionally forward the logs to an external archive server 
instead. In this case the logs would be "cached" on the lab controller (not 
sent to the server) and then moved to the archive server when the recipe set is 
finished.

This "caching" behaviour is now unconditional. That is, logs are always stored 
on the lab controller. This is sufficient for small sites, and is effectively 
the same if the server and lab controller are the same system. If an archive 
server is configured and beaker-transfer is enabled, then logs are moved there.

The ``CACHE`` setting in ``/etc/beaker/labcontroller.conf``, which previously 
controlled this behaviour, no longer has any effect and can be removed.
