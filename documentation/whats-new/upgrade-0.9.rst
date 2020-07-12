Upgrading to Beaker 0.9
=======================

These notes describe the steps needed to upgrade your Beaker installation from 
version 0.8.2 to version 0.9.3.

For older upgrade instructions, refer to the obsolete `SchemaUpgrades directory 
<https://github.com/beaker-project/beaker/tree/master/SchemaUpgrades/>`_ in Beaker's
source tree.

Database changes
++++++++++++++++

New distros schema
------------------

This upgrade requires that all existing distros be re-imported into Beaker.
Ensure that you have an up-to-date database backup before proceeding.

::

    -- distro becomes distro_tree
    RENAME TABLE distro TO distro_tree;

    -- create distro table from existing distro_trees
    CREATE TABLE distro
        (id INT NOT NULL AUTO_INCREMENT,
        name VARCHAR(255) NOT NULL,
        osversion_id INT NOT NULL,
        date_created DATETIME NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (name),
        CONSTRAINT distro_osversion_id_fk
            FOREIGN KEY (osversion_id) REFERENCES osversion (id))
        ENGINE=InnoDB
        SELECT NULL AS id, name, MAX(osversion_id) AS osversion_id, UTC_TIMESTAMP() AS date_created
            FROM distro_tree
            GROUP BY name;
    ALTER TABLE distro_tree
        DROP FOREIGN KEY distro_tree_ibfk_1, -- breed_id fk
        DROP FOREIGN KEY distro_tree_ibfk_3, -- osversion_id fk
        DROP install_name,
        DROP breed_id,
        DROP osversion_id,
        DROP virt,
        MODIFY arch_id INT NOT NULL,
        MODIFY date_created DATETIME NOT NULL,
        ADD distro_id INT DEFAULT NULL AFTER id,
        ADD ks_meta TEXT AFTER variant,
        ADD kernel_options TEXT AFTER ks_meta,
        ADD kernel_options_post TEXT AFTER kernel_options;
    -- If your schema is old, it might still contain an obsolete "method" column as well:
    --ALTER TABLE distro_tree DROP method;
    UPDATE distro_tree
        INNER JOIN distro ON distro_tree.name = distro.name
        SET distro_tree.distro_id = distro.id;
    ALTER TABLE distro_tree
        DROP name,
        MODIFY distro_id INT NOT NULL,
        ADD CONSTRAINT distro_tree_distro_id_fk
            FOREIGN KEY (distro_id) REFERENCES distro (id);

    -- In the following upgrades, we merge duplicate distro_trees into the
    -- lowest matching id, so that we can clean them up below and add a
    -- uniqe constraint.

    -- distro_activity becomes distro_tree_activity, with duplicates merged
    RENAME TABLE distro_activity TO distro_tree_activity;
    ALTER TABLE distro_tree_activity
        ADD distro_tree_id INT DEFAULT NULL AFTER distro_id,
        ADD CONSTRAINT distro_tree_activity_distro_tree_id_fk
            FOREIGN KEY (distro_tree_id) REFERENCES distro_tree (id);
    UPDATE distro_tree_activity
        INNER JOIN distro_tree ON distro_tree_activity.distro_id = distro_tree.id
        -- this is the least-row-per-group trick
        INNER JOIN (
            SELECT MIN(id) AS id, distro_id, arch_id, variant
            FROM distro_tree
            GROUP BY distro_id, arch_id, variant) AS x
            ON x.distro_id = distro_tree.distro_id
                AND x.arch_id = distro_tree.arch_id
                AND x.variant <=> distro_tree.variant
        SET distro_tree_activity.distro_tree_id = x.id;
    ALTER TABLE distro_tree_activity
        DROP FOREIGN KEY distro_tree_activity_ibfk_2, -- distro_id fk
        DROP distro_id;
    UPDATE activity
        SET type = 'distro_tree_activity'
        WHERE type = 'distro_activity';

    -- recipe.distro_id becomes recipe.distro_tree_id
    ALTER TABLE recipe
        ADD distro_tree_id INT DEFAULT NULL AFTER distro_id,
        ADD CONSTRAINT recipe_distro_tree_id_fk
            FOREIGN KEY (distro_tree_id) REFERENCES distro_tree (id);
    UPDATE recipe
        INNER JOIN distro_tree ON recipe.distro_id = distro_tree.id
        INNER JOIN (
            SELECT MIN(id) AS id, distro_id, arch_id, variant
            FROM distro_tree
            GROUP BY distro_id, arch_id, variant) AS x
            ON x.distro_id = distro_tree.distro_id
                AND x.arch_id = distro_tree.arch_id
                AND x.variant <=> distro_tree.variant
        SET recipe.distro_tree_id = x.id;
    ALTER TABLE recipe
        DROP FOREIGN KEY recipe_ibfk_3, -- distro_id fk
        DROP distro_id;

    -- system.reprovision_distro_id becomes system.reprovision_distro_tree_id
    ALTER TABLE system
        ADD reprovision_distro_tree_id INT DEFAULT NULL AFTER reprovision_distro_id,
        ADD CONSTRAINT system_reprovision_distro_tree_id_fk
            FOREIGN KEY (reprovision_distro_tree_id) REFERENCES distro_tree (id);
    UPDATE system
        INNER JOIN distro_tree ON system.reprovision_distro_id = distro_tree.id
        INNER JOIN (
            SELECT MIN(id) AS id, distro_id, arch_id, variant
            FROM distro_tree
            GROUP BY distro_id, arch_id, variant) AS x
            ON x.distro_id = distro_tree.distro_id
                AND x.arch_id = distro_tree.arch_id
                AND x.variant <=> distro_tree.variant
        SET system.reprovision_distro_tree_id = x.id;
    ALTER TABLE system
        DROP FOREIGN KEY system_ibfk_1, -- reprovision_distro_id fk
        DROP reprovision_distro_id;

    -- this table is replaced by distro_tree_lab_controller_map
    DROP TABLE distro_lab_controller_map;

    -- move tags from distro_tree to distro
    CREATE TABLE distro_tag_map_new
        (distro_id INT NOT NULL,
        distro_tag_id INT NOT NULL,
        PRIMARY KEY (distro_id, distro_tag_id),
        CONSTRAINT distro_tag_map_distro_id_fk
            FOREIGN KEY (distro_id) REFERENCES distro (id)
            ON UPDATE CASCADE ON DELETE CASCADE,
        CONSTRAINT distro_tag_map_distro_tag_id_fk
            FOREIGN KEY (distro_tag_id) REFERENCES distro_tag (id)
            ON UPDATE CASCADE ON DELETE CASCADE)
        ENGINE=InnoDB
        SELECT DISTINCT distro.id AS distro_id, distro_tag_map.distro_tag_id
            FROM distro_tag_map
            INNER JOIN distro_tree ON distro_tag_map.distro_id = distro_tree.id
            INNER JOIN distro ON distro_tree.distro_id = distro.id;
    DROP TABLE distro_tag_map;
    RENAME TABLE distro_tag_map_new TO distro_tag_map;

    -- remove the duplicate distro_trees
    DELETE FROM distro_tree
        USING distro_tree
        INNER JOIN (
            SELECT MIN(id) AS id, distro_id, arch_id, variant
            FROM distro_tree
            GROUP BY distro_id, arch_id, variant) AS x
            ON x.distro_id = distro_tree.distro_id
                AND x.arch_id = distro_tree.arch_id
                AND x.variant <=> distro_tree.variant
        WHERE distro_tree.id != x.id;
    ALTER TABLE distro_tree
        ADD UNIQUE (distro_id, arch_id, variant);

    -- we don't store breed anymore
    DROP TABLE breed;

    -- these are unused
    ALTER TABLE lab_controller
        DROP distros_md5,
        DROP systems_md5;

Then run :program:`beaker-init` to create the new distro tables.

Finally, import distros using the :program:`beaker-import` command on each lab 
controller.


Provision via the command queue
-------------------------------

Run the following SQL::

    ALTER TABLE command_queue
        ADD delay_until DATETIME AFTER task_id,
        ADD distro_tree_id INT NULL,
        ADD kernel_options TEXT NULL,
        ADD CONSTRAINT command_queue_distro_tree_id_fk
            FOREIGN KEY (distro_tree_id)
            REFERENCES distro_tree (id);
    ALTER TABLE recipe
        ADD rendered_kickstart_id INT NULL AFTER system_id,
        ADD CONSTRAINT recipe_rendered_kickstart_id_fk
            FOREIGN KEY (rendered_kickstart_id)
            REFERENCES rendered_kickstart (id);


Cobbler credentials are not needed
----------------------------------

Run the following SQL::

    ALTER TABLE lab_controller
        DROP username,
        DROP password;


Expand CPU flag column (:issue:`782284`)
--------------------------------------------

Run the following SQL::

    ALTER TABLE cpu_flag
        MODIFY flag VARCHAR(255) DEFAULT NULL;

To roll back::

    ALTER TABLE cpu_flag
        MODIFY flag VARCHAR(10) DEFAULT NULL;


Remove activity rows for deleted groups (:issue:`840724`)
-------------------------------------------------------------

This will remove rows that fail the new non-NULLable constraint of 
``group_activity.group_id``. Run the following SQL::

    DELETE FROM group_activity WHERE group_id IS NULL;
    DELETE FROM activity WHERE type = 'group_activity'
        AND id NOT IN (SELECT id FROM group_activity);
    ALTER TABLE group_activity
        MODIFY group_id int(11) NOT NULL;

We can only rollback our group_activity.group_id modification. To roll back::

    ALTER TABLE group_activity
        MODIFY group_id int(11) NULL;


ARM support in beaker-provision (:issue:`841969`)
-----------------------------------------------------

Run the following SQL::

    ALTER TABLE system
	ADD kernel_type_id INT(11) NOT NULL;
    UPDATE system set kernel_type_id = (SELECT id FROM kernel_type WHERE kernel_type = 'default');
    ALTER TABLE system
	ADD CONSTRAINT system_kernel_type_id_fk
	    FOREIGN KEY (kernel_type_id) REFERENCES kernel_type (id);
    ALTER TABLE distro_tree_image
	MODIFY image_type enum('kernel','initrd','live','uimage','uinitrd') NOT NULL,
	ADD kernel_type_id INT(11) NOT NULL;
    UPDATE distro_tree_image set kernel_type_id = (SELECT id FROM kernel_type WHERE kernel_type = 'default');
    ALTER TABLE distro_tree_image
	ADD CONSTRAINT distro_tree_image_kernel_type_id_fk
	    FOREIGN KEY (kernel_type_id) REFERENCES kernel_type (id),
        DROP PRIMARY KEY,
	ADD PRIMARY KEY (distro_tree_id, image_type,kernel_type_id);

To roll back::

    ALTER TABLE system
	DROP kernel_type_id,
	DROP FOREIGN KEY system_kernel_type_id_fk;
    ALTER TABLE distro_tree_image
	DROP PRIMARY KEY,
	DROP kernel_type_id,
	DROP FOREIGN KEY distro_tree_image_kernel_type_id_fk,
	ADD PRIMARY KEY (distro_tree_id, image_type);
    DROP TABLE kernel_type;


.. _cobbler-migration:

Migrating Cobbler configuration
+++++++++++++++++++++++++++++++


Default root password for installed systems
-------------------------------------------

Since version 0.8.2 the root password for installed systems can be set globally 
by the Beaker administrator, as well as individually by each user. However if 
no password was set, the Cobbler default root password was inherited from the 
``default_password_crypted`` setting in :file:`/etc/cobbler/settings`.

If you have not already set a global root password in Beaker, you may want to 
set it to the same password configured in Cobbler.


Default kernel options
----------------------

Cobbler allows site-wide default kernel options to be configured in the 
``kernel_options`` setting in :file:`/etc/cobbler/settings`. If you have 
modified these, you may want to apply the same defaults in Beaker by setting 
``beaker.kernel_options`` in :file:`/etc/beaker/server.cfg`.

In addition, Cobbler has default kernel options specifically for S/390 systems 
in the ``kernel_options_s390x`` setting, which default to::

    RUNKS=1 ramdisk_size=40000 root=/dev/ram0 ro ip=off vnc

If you are the lucky owner of an S/390 mainframe you should set these kernel 
options in the Install Options tab for your S/390 systems.


Install options for Cobbler distros
-----------------------------------

If you have set kickstart metadata, kernel options, or post-install kernel 
options for any distros in Cobbler (for example using ``cobbler distro edit``) 
you will need to find the equivalent distro tree in Beaker's web UI and set the 
options there. The format and meaning of the install options in Beaker are the 
same as in Cobbler.


Power scripts
-------------

When executing power commands, Beaker uses shell scripts which are based on 
Cobbler's power templates which are installed in :file:`/etc/cobbler/power`. If 
you have customised any of Cobbler's power templates you may need to add 
a custom Beaker power script with the same modifications. Refer to 
:ref:`customizing-power-commands` in the Administration Guide.

Note that Beaker uses shell scripts rather than Cheetah templates for power 
commands, even though the shell scripts look very similar because the variable 
names are the same. You can examine the default scripts in 
:file:`/usr/lib/python2.6/​site-packages/​bkr/​labcontroller/​power-scripts` 
for inspiration.


Netboot config files
--------------------

Beaker does not use templates for generating bootloader configs when 
provisioning a system (Cobbler's :file:`/etc/cobbler/pxe/pxesystem.template` 
etc). Customizing these configs is not supported.

Unlike Cobbler, Beaker does *not* manage the default bootloader config 
(:file:`$TFTP_ROOT/​pxelinux.cfg/​default`, and equivalent files for 
other bootloaders). You can continue to let Cobbler put its PXE menu here, or 
you can manage this file by hand. Beaker's only requirement for automated 
provisioning is that it must default to local booting with a sensible timeout 
(the Cobbler PXE menu does this).


Snippets
--------

Snippets are now located on the Beaker server (rather than the lab controller), 
under :file:`/etc/beaker/snippets`.

Beaker uses Jinja2 for templating, so templates will need to be rewritten. 
Refer to the `Jinja2 documentation <http://jinja.pocoo.org/docs/>`_ for details 
of the template syntax, and to :ref:`kickstarts` in the Administration Guide 
for details about the Beaker specifics.

For your convenience, some common Cobbler template constructs are shown below, 
along with their equivalent in Beaker.

Accessing a variable::

    $getVar('ondisk', '')

    {{ ondisk }}

Looping::

    #set _devices = $getVar('scsidevices', '').split(',')
    #for $device in $_devices:
    device $device
    #end for

    {% for device in scsidevices|split(',') %}
    device {{ device }}
    {% endfor %}

Conditional on distro version::

    #if $os_version == "rhel3"
    #set $yum = "yum-2.2.2-1.rhts.EL3.noarch.rpm"
    #end if

    {% if distro is osmajor('RedHatEnterpriseLinux3') %}
    {% set yum = 'yum-2.2.2-1.rhts.EL3.noarch.rpm' %}
    {% endif %}


Other Cobbler system management features
----------------------------------------

Cobbler's func integration, managed config files, and RHN registration features 
are incompatible with Beaker.

DHCP and DNS services are outside the scope of Beaker, so if you are using 
Cobbler to manage these in the lab then you can continue to do so. However, if 
you are relying on Cobbler's network config scripts when provisioning systems 
(that is, the ``pre_install_network_config``, ``network_config``, and 
``post_install_network_config`` snippets) you must migrate this configuration 
to DHCP instead.

If a system has particular network configuration needs not covered by DHCP, you 
can add a per-system snippet for it as appropriate: ``system_pre`` for 
pre-installation scripts, ``network`` for Anaconda network commands, or 
``system_post`` for post-installation scripts. Refer to :ref:`kickstarts` in 
the Administration Guide for details.
