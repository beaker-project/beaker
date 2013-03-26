oVirt data center mapping
=========================

In previous versions, Beaker looked for usable oVirt data centers by matching 
against the lab controller FQDN (with some modifications to match oVirt naming 
constraints). Now the mapping from lab controllers to oVirt data centers is 
maintained in the Beaker database. This allows you to utilize multiple oVirt 
data centers per lab. See :ref:`ovirt` for details about how to configure the 
mapping.
