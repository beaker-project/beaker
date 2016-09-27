beaker-create-ipxe-image: Generate and upload iPXE boot image to Glance
=======================================================================

.. program:: beaker-create-ipxe-image

Synopsis
--------

| :program:`beaker-create-ipxe-image` [*options*]

Description
-----------

Generates a bootable image containing the iPXE network boot loader, and 
a configuration pointing at this Beaker instance.

Beaker uses this image as part of the support for provisioning dynamic VMs in 
OpenStack. The image needs to be created once when OpenStack integration is 
enabled. The credentials given here need to have the permission to create a public
image in OpenStack.

This command requires read access to the Beaker server configuration. Run it as 
root or as another user with read access to the configuration file.

Options
-------

.. option:: --os-username <username>, --os-password <password>, --os-tenant-name <name>

   OpenStack credentials for uploading the generated image to Glance.

.. option:: --no-upload

   Do not upload the generated image to OpenStack. The image temp file is left 
   on disk and its filename is printed. Use this if you need to examine or 
   manipulate the image before uploading it to Glance manually.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Once OpenStack integration is configured (see :ref:`openstack`), create 
a suitable iPXE image in Glance::

    beaker-create-ipxe-image \
        --os-username beaker \
        --os-password beaker \
        --os-tenant-name Beaker
