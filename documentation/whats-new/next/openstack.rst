OpenStack
=========

Beaker's experimental support for running recipes on dynamically created VMs 
has been ported from oVirt to OpenStack.

Database changes
----------------

Run :program:`beaker-init` to create the new table.

Run the following SQL::

    ALTER TABLE tg_user
        ADD openstack_username VARCHAR(255) AFTER rootpw_changed,
        ADD openstack_password VARCHAR(2048) AFTER openstack_username,
        ADD openstack_tenant_name VARCHAR(2048) AFTER openstack_password;

    ALTER TABLE virt_resource
        ADD instance_id BINARY(16) NOT NULL AFTER id,
        ADD kernel_options VARCHAR(2048) AFTER lab_controller_id;

To roll back, run the following SQL::

    DROP TABLE openstack_region;

    ALTER TABLE tg_user
        DROP openstack_username,
        DROP openstack_password,
        DROP openstack_tenant_name;

    ALTER TABLE virt_resource
        DROP instance_id,
        DROP kernel_options;

You can optionally run the following SQL to drop oVirt-related structures that 
are no longer required. This step cannot be rolled back.

::

    ALTER TABLE virt_resource
        DROP system_name,
        DROP mac_address;

    DROP TABLE lab_controller_data_center;

    DELETE FROM config_item
    WHERE name IN ('default_guest_memory', 'default_guest_disk_size');


Configuration changes
---------------------

Add the following directive to the section in 
:file:`/etc/httpd/conf.d/beaker-server.conf` for redirecting to HTTPS. This 
ensures that iPXE can fetch scripts over plain HTTP.

::

    RewriteCond %{REQUEST_URI} !/ipxe-script$ [NC]
