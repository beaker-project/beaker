.. _ovirt:
.. _openstack:

Integration with OpenStack
==========================

.. note::

   The OpenStack integration for dynamic system provisioning is classified as
   experimental. It has a number of limitations and may impact the scheduler's
   performance, therefore it is currently not recommended for use in production
   on large Beaker instances.

Beaker can optionally be configured to use OpenStack to create
virtual machines on demand for running recipes.

When OpenStack integration is enabled, Beaker will attempt to create a new
virtual machine for each recipe when it is scheduled. If creating the virtual
machine fails, Beaker will fall back to using the regular hardware
pool for that recipe. Recipes with hardware requirements in
``<hostRequires/>`` which cannot be satisfied by a virtual machine are
excluded from this process.

Package prerequisites
---------------------

- python-keystoneclient >= 3.10.0
- python-novaclient >= 7.1.2
- python-glanceclient >= 2.6.0
- python-neutronclient >= 6.1.1

As RHEL 7 may not provide the required version of those packages, you can use
Ocata EL7 repositories provided by CentOS in this case. See
`CentOS OpenStack Wiki <https://wiki.centos.org/Cloud/OpenStack/>`_
for more details.

Configuring OpenStack integration
---------------------------------

To enable OpenStack integration, configure the Identity API (Keystone) endpoint,
dashboard (Horizon) URL and an OpenStack account of Beaker in :file:`/etc/beaker/server.cfg`::

    # Use OpenStack for running recipes on dynamically created guests.
    # Beaker uses the credentials given here to authenticate to OpenStack
    # when creating OpenStack instances on behalf of users.
    openstack.identity_api_url = 'https://openstack.example.com:13000/v3'
    openstack.dashboard_url = 'https://openstack.example.com/dashboard/'
    openstack.username = ""
    openstack.password = ""

The user domain name when authenticating to OpenStack. Beaker does not
provide a default domain name. This option is required if the OpenStack
instance has been configured to require a domain name.

    openstack.user_domain_name = ""

The OpenStack external network name for the instance. If not provided, Beaker
will search for an external network and use the first one it finds.

    openstack.external_network_name = ""

By default, Beaker will attempt to set up a floating IP address for a newly
created instance to provide a public IP address. This assumes that the IP
address assigned when the instance is created is on a private network. If the
'create_floating_ip' flag is set to False, the Beaker code will use the IP
address assigned when the instance is created as the public IP address of the
instance.

    openstack.create_floating_ip = True

Currently Beaker does not support multiple OpenStack regions. Beaker expects
a single row to exist in the ``openstack_region`` table, referencing the lab
controller which should be used for OpenStack recipes. You must insert the row
manually::

    INSERT INTO openstack_region (lab_controller_id)
    SELECT id FROM lab_controller WHERE fqdn = 'lab.example.com';

Uploading iPXE image to Glance
------------------------------

In order to boot distro installers on OpenStack instances, Beaker relies on
a special image containing the iPXE network boot loader, which then loads its
boot configuration from the Beaker server. The
:program:`beaker-create-ipxe-image` tool creates and uploads a suitable image
to Glance. You must run this tool once after defining an OpenStack region.

The name for each virtual machine is constructed from the ``guest_name_prefix``
setting (see :ref:`admin-configuration`) combined with the recipe ID. If you
have configured multiple Beaker instances to use the same OpenStack instance,
make sure you set a distinct value for ``guest_name_prefix`` to avoid name
collisions.
