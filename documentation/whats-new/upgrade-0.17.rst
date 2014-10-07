Upgrading to Beaker 0.17
========================

Configuration changes
---------------------

iPXE scripts over HTTP
~~~~~~~~~~~~~~~~~~~~~~

Add the following directive to the section in 
:file:`/etc/httpd/conf.d/beaker-server.conf` for redirecting to HTTPS. This 
ensures that iPXE can fetch scripts over plain HTTP.

::

    RewriteCond %{REQUEST_URI} !/ipxe-script$ [NC]

New cache directory for web assets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to support customizable themes, the Beaker web application now builds 
web assets at runtime instead of during the package build process. As a result, 
generated assets are now located in a different directory 
(:file:`/var/cache/beaker/assets` rather than 
:file:`/usr/share/bkr/server/assets/generated`).

The Apache configuration in :file:`/etc/httpd/conf.d/beaker-server.conf` must 
be updated to reflect the new location for generated assets.

Add a new ``Alias`` directive *before* the existing ``Alias`` for 
``/bkr/assets``. Remember to remove or adjust the ``/bkr`` prefix as 
appropriate for your installation.

::

    Alias /bkr/assets/generated /var/cache/beaker/assets

Replace the existing ``<Directory /usr/share/bkr/server/assets/generated>`` 
section with the following::

    <Directory /var/cache/beaker/assets>
        <IfModule mod_authz_core.c>
            # Apache 2.4
            Require all granted
        </IfModule>
        <IfModule !mod_authz_core.c>
            # Apache 2.2
            Order deny,allow
            Allow from all
        </IfModule>
        # Generated assets have a content hash in their filename so they can
        # safely be cached forever.
        ExpiresActive on
        ExpiresDefault "access plus 1 year"
    </Directory>

Database changes
----------------

To upgrade the database schema for Beaker 0.17, first run 
:program:`beaker-init` to create the new tables. Then run the following SQL 
statements.

.. note:: In established Beaker instances the ``recipe_task`` and ``recipe`` 
   tables may be very large, and therefore these upgrade steps may take a long 
   time. Allow approximately 1 minute per 500 000 rows in the ``recipe_task`` 
   table, and approximately 1 minute per 100 000 rows in the ``recipe`` table.

::

    ALTER TABLE tg_user
        DROP KEY email_address,
        ADD INDEX email_address (email_address),
        ADD openstack_username VARCHAR(255) AFTER rootpw_changed,
        ADD openstack_password VARCHAR(2048) AFTER openstack_username,
        ADD openstack_tenant_name VARCHAR(2048) AFTER openstack_password;

    ALTER TABLE virt_resource
        ADD instance_id BINARY(16) NOT NULL AFTER id,
        ADD kernel_options VARCHAR(2048) AFTER lab_controller_id;

    ALTER TABLE lab_controller ADD UNIQUE KEY uc_user_id (user_id);

    ALTER TABLE job
        ADD ntasks INT AFTER ttasks,
        MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',
            'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted', 
            'Reserved') NOT NULL;

    ALTER TABLE recipe_set
        ADD ntasks INT AFTER ttasks,
        MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',
            'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted', 
            'Reserved') NOT NULL;

    ALTER TABLE recipe
        ADD ntasks INT AFTER ttasks,
        MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',
            'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted', 
            'Reserved') NOT NULL;

    ALTER TABLE recipe_task
        MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',
            'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted', 
            'Reserved') NOT NULL;

To roll back, run the following SQL. If duplicate user email addresses have 
been entered since the upgrade, you must first manually adjust them before 
restoring the UNIQUE constraint.

::

    ALTER TABLE tg_user
        DROP INDEX email_address,
        ADD UNIQUE email_address (email_address),
        DROP openstack_username,
        DROP openstack_password,
        DROP openstack_tenant_name;

    ALTER TABLE virt_resource
        DROP instance_id,
        DROP kernel_options;

    ALTER TABLE lab_controller
        DROP KEY uc_user_id,
        ADD KEY (user_id);

    ALTER TABLE job
        DROP ntasks,
        MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',
            'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted')
            NOT NULL;

    ALTER TABLE recipe_set
        DROP ntasks,
        MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',
            'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted')
            NOT NULL;

    ALTER TABLE recipe
        DROP ntasks,
        MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',
            'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted')
            NOT NULL;

    ALTER TABLE recipe_task
        MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',
            'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted')
            NOT NULL;

    DROP TABLE job_activity;

    DROP TABLE recipe_reservation;

    DROP TABLE openstack_region;

You can optionally run the following SQL to drop oVirt-related structures that 
are no longer required. This step cannot be rolled back.

::

    ALTER TABLE virt_resource
        DROP system_name,
        DROP mac_address;

    DROP TABLE lab_controller_data_center;

    DELETE FROM config_item
    WHERE name IN ('default_guest_memory', 'default_guest_disk_size');
