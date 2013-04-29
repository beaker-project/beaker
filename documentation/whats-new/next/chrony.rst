Chrony is enabled on Fedora and RHEL7
=====================================

The chrony clock synchronization daemon is now installed and enabled by default 
for recipes running on Fedora and Red Hat Enterprise Linux 7, where the ntp 
daemon is no longer available. In addition, the harness is now configured to 
wait for clock synchronization before it starts.

If you want to opt out of this behaviour (for example, if the presence of the 
chrony package interferes with your testing) you can pass 
``ks_meta="no_clock_sync"`` in your job XML.
