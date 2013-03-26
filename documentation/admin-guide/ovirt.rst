.. _ovirt:

Integration with oVirt Engine and RHEV-M
========================================

Beaker can optionally be configured to use oVirt Engine (or the
equivalent Red Hat Enterprise Virtualization Manager product) to create
virtual machines on demand for running recipes. Version 3.0 or higher of
the product is required.

To enable oVirt integration, you must configure the API endpoint and
credentials in ``/etc/beaker/server.cfg``:

::

    # Enable oVirt integration, for running recipes on dynamically created guests
    ovirt.enabled = True
    ovirt.api_url = 'https://manager.example.com:8443/api'
    ovirt.username = 'admin@internal'
    ovirt.password = 'example'

When oVirt integration is enabled, Beaker will attempt to create a new
virtual machine for each recipe when it is scheduled. If the oVirt
Engine is over capacity, or if creating the virtual machine fails for
any other reason, Beaker will fall back to using the regular hardware
pool for that recipe. Recipes with hardware requirements in
``<hostRequires/>`` which cannot be satisfied by a virtual machine are
excluded from this process.

Each lab controller in Beaker can have zero or more oVirt data centers 
associated with it. Beaker will try each of the data centers when provisioning 
a recipe. In a future release this will be configurable in the web UI, but for 
now you must manually define the data centers in the database. For example::

    INSERT INTO lab_controller_data_center
        (lab_controller_id, data_center, storage_domain)
    VALUES
        ((SELECT id FROM lab_controller WHERE fqdn = 'lab.example.com'),
         'my_data_center', 'my_storage_domain');

The default memory and disk size allocated to virtual machines is
controlled by the ``default_guest_memory`` and
``default_guest_disk_size`` settings (see :ref:`admin-configuration`). The name 
for each virtual machine is constructed from the ``guest_name_prefix`` setting 
combined with the recipe ID. If you have configured multiple Beaker instances 
to use the same oVirt Engine instance, make sure you set a distinct value for 
``guest_name_prefix`` to avoid name collisions.

Beaker requires that autofs be enabled and configured to manage ``/net``
on the hypervisors, so that they can access installer images when
starting a recipe. Note that this makes Red Hat Enterprise
Virtualization Hypervisor (RHEV-H) unsuitable for running Beaker
recipes, because ``yum`` is not available to install arbitrary packages.
Use RHEL for the hypervisors instead.
