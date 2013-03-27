Live role environment variables
===============================

The ``RECIPE_MEMBERS`` environment variable and any other role environment 
variables are now updated at the start of every task. In particular, this makes 
it possible to do multi-host testing between guest recipes and their host. The 
guest FQDNs will be available on the host for tasks executed after the guests 
have finished installing (in most cases, after the 
``/distribution/virt/install`` task).

Related bug: :issue:`887283`
