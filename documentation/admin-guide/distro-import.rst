.. _importing-distros:

Importing distros
=================

In order for a distro to be usable in Beaker, it must be "imported". Importing 
a distro into Beaker registers the location(s) from which the distro tree is 
available in the lab, along with various metadata about the distro.

To import a distro, run ``beaker-import`` on the lab controller and pass all 
the URLs under which the distro is available. For example::

    beaker-import \
        http://mymirror.example.com/pub/fedora/linux/releases/17/Fedora/ \
        ftp://mymirror.example.com/pub/fedora/linux/releases/17/Fedora/  \
        nfs://mymirror.example.com:/pub/fedora/linux/releases/17/Fedora/

Distros must be imported separately on each lab controller, and you can import 
from a different set of URLs in each lab. This allows you to import distros 
from the nearest mirror in each lab.

When importing, at least one of the URLs has to be type of ``http``, ``https``
or ``ftp``. Specifying only ``nfs`` won't work, since it's currently not supported
as a valid primary install method.

Normally a distro will have a :file:`.composeinfo` or :file:`.treeinfo` file, which
provides metadata required by :program:`beaker-import`. If those files are not available
you can perform a "naked" import by specifying ``--family``,
``--version``, ``--name``, ``--arch``, ``--kernel``, ``--initrd``. See
:doc:`beaker-import <man/beaker-import>` for more details.

You can check that the distros were added successfully by browsing the Distros 
page (see :ref:`distros`).

Fetching harness packages
-------------------------

The first time you import a new distro family you will need to run 
:program:`beaker-repo-update` on the server to populate the harness repo for 
the new distro family.
See :doc:`beaker-repo-update <man/beaker-repo-update>` for more details.

If the distro family is not currently supported by Beaker (for example, if it 
is a derivative of Fedora or Red Hat Enterprise Linux with a different name) 
you can instead create a symlink for the harness repo, pointing at an existing 
compatible distro family::

    ln -s RedHatEnterpriseLinux6 /var/www/beaker/harness/MyCustomDistro6

.. _distro-features:

Install options for distro features
-----------------------------------

Beaker uses a number of kickstart metadata variables to determine which 
features are supported by the distro, in order to generate valid kickstarts and 
scripts when provisioning.

If the distro is supported by Beaker, the distro family will be recognised by 
name and the correct install options will be automatically populated. In this 
case you do not need to explicitly set them. Beaker will generate valid 
kickstarts without any further intervention.

However, if Beaker does not recognize the distro, it will be assumed to have 
all the latest features (essentially equivalent to the latest Fedora release). 
If necessary, you can use the :ref:`OS versions page <admin-os-versions>` to 
set install options for the distro family.

For example, if you import a custom distro based on Red Hat Enterprise Linux 6, 
you should set the following kickstart metadata variables on your custom distro 
family.
This indicates that the distro does not use systemd or chrony, and that the 
installer does not support ``autopart --type`` or ``bootloader 
--leavebootorder``.

::

    !has_systemd !has_chrony !has_autopart_type !has_leavebootorder

Support for Project Atomic distros
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable :ref:`atomic-host`, two install options must be set for Project Atomic
distros: ``has_rpmostree`` and ``bootloader_type=extlinux``.

Refer to the documentation about :ref:`kickstart metadata  
<kickstart-metadata-distro-features>` for a complete list of variables relating 
to distro features.

.. _stable-distro-tagging:

Automated jobs for new distros
------------------------------

Beaker has a facility for running scripts whenever a new distro is imported, 
provided by the ``beaker-lab-controller-addDistro`` package.
After installing that package, scripts placed in the 
``/var/lib/beaker/addDistro.d`` directory will be run each time a distro is 
imported.

Beaker ships with a script, ``/var/lib/beaker/addDistro.d/updateDistro``, which 
schedules a Beaker job to test installation of the new distro and tags it with 
``STABLE`` if the job completes without error. Use this as a guide for creating 
more specific jobs that you might find useful.

.. note:: The ``updateDistro`` script assumes that the Beaker client is 
   correctly configured on the lab controller. See :ref:`installing-bkr-client`.

.. _pxe-menu:

Generating a boot menu
----------------------

Beaker includes a command, ``beaker-pxemenu``, which can be run on the lab 
controller to generate a boot menu containing the distros in Beaker. Users in 
the lab can then perform manual installations by selecting a distro from the 
menu. Boot menus are generated for ``menu.c32`` (PXELINUX), EFI GRUB, 64-bit
ARM and 64-bit PowerPC.

You can limit the menu to only contain distros tagged in Beaker with a
certain tag, by passing the ``--tag`` option to ``beaker-pxemenu``. By
default, all distros which are available in the lab are included in the
menu.

.. note:: If you have configured a non-default TFTP root directory in 
   ``/etc/beaker/labcontroller.conf``, be sure to pass that same directory in 
   the ``--tftp-root`` option to ``beaker-pxemenu``.

If you are using a boot menu, you should edit the PXELINUX default 
configuration :file:`pxelinux.cfg/default` to boot from local disk by default, 
with an option to load the menu. For example::

    default local
    prompt 1
    timeout 200

    say ***********************************************
    say Press ENTER to boot from local disk
    say Type "menu" at boot prompt to view install menu
    say ***********************************************

    label local
        localboot 0

    label menu
        kernel menu.c32
        append pxelinux.cfg/beaker_menu

Similarly, you should edit the default configuration for 64-bit ARM 
:file:`aarch64/grub.cfg` to exit after a timeout, with an option to load the 
menu. For example::

    set default="Exit PXE"
    set timeout=10
    menuentry "Exit PXE" {
        exit
    }
    menuentry "Install distro from Beaker" {
        configfile aarch64/beaker_menu.cfg
    }

If you are using GRUB2 boot menus, you should edit the default configuration for
x86 EFI :file:`boot/grub2/grub.cfg` to exit after a timeout, with an option to
load the menus. For example::

    set default="Exit PXE"
    set timeout=60
    menuentry "Exit PXE" {
        exit
    }
    menuentry "Install distro from Beaker (x86)" {
        configfile boot/grub2/beaker_menu_x86.cfg
    }

Likewise, you should edit the default configuration for iPXE :file:'ipxe/default'
to exit after a timeout with an option to load the menu.  Also, iPXE will not
load the host specific script by default like PXELINUX, so we direct it to do
that in the default script if available, for example:

    #!ipxe

    chain /ipxe/${ip:hexraw} ||
    prompt --key m --timeout 60000 Press 'm' to view install menu, any other key to boot from local disk && set beaker 1 || clear beaker
    isset ${beaker} && chain /ipxe/beaker_menu ||
    iseq ${builtin/platform} pcbios && sanboot --no-describe --drive 0x80 ||
    exit 1

If your site imports distros into Beaker infrequently, you may prefer to
run ``beaker-pxemenu`` after importing new distros. Otherwise, you can
create a cron job to periodically update the PXE menu::

    #!/bin/sh
    exec beaker-pxemenu --quiet
