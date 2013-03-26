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

For Beaker’s purposes, each data center in oVirt must correspond to a
Beaker lab. The data center name should match the Beaker lab
controller’s FQDN. To meet oVirt’s naming constraints for data centers,
periods in the FQDN should be replaced with underscores and the name
truncated to 40 characters. For example, if your Beaker lab controller’s
FQDN is lab.beaker.engineering.mylocation.example.com, the corresponding
oVirt data center should be named
``lab_beaker_engineering_mylocation_exampl``. Beaker will ignore data
centers whose name does not correspond to a lab controller.

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
