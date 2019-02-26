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

.. option:: --os-username <username>

   OpenStack user name for establishing a new trust between Beaker and the
   given user.

.. option:: --os-password <password>

   OpenStack user password for establishing a new trust between Beaker and
   the given user.

.. option:: --os-project-name <project-name>

   OpenStack project name for establishing a new trust between Beaker and
   the given user.

.. option:: --os-user-domain-name <user-domain-name>

   OpenStack user domain name for establishing a new trust between Beaker
   and the given user.

.. option:: --os-project-domain-name <project-domain-name>

   OpenStack project domain name for establishing a new trust between Beaker
   and the given user.

.. option:: --no-upload

   Do not upload the generated image to OpenStack. The image temp file is left
   on disk and its filename is printed. Use this if you need to examine or
   manipulate the image before uploading it to Glance manually.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

OpenStack integration must be configured (see :ref:`openstack`) before running
this command.

This command creates an iPXE image in Glance where the OpenStack
authentication uses default domain information::

    beaker-create-ipxe-image \
        --os-username beaker \
        --os-password beaker \
        --os-project-name beaker

Use the options shown in this command when OpenStack requires user and project
domain names::

    beaker-create-ipxe-image \
        --os-username beaker \
        --os-password beaker \
        --os-project-name beaker \
        --os-user-domain-name=domain.com \
        --os-project-domain-name=domain.com
