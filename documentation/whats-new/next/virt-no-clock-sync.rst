Network time syncing is disabled for VMs
========================================

For guest recipes and recipes running on dynamic VMs, Beaker no longer includes 
the kickstart snippet for ensuring a network time synchronization service (ntpd 
or chrony) is installed and enabled. In these cases, the recipe is running on 
a freshly created VM whose clock will be correctly synchronized from the host, 
so network time synchronization is not necessary (and in some cases, may cause 
extra delays).
