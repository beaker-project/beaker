TFTP files and directories
==========================

As part of the :ref:`provisioning process <provisioning-process>`, test systems
fetch boot loader images and configuration files over TFTP from the Beaker lab
controller.
This section describes all the files under the TFTP root directory that the
:program:`beaker-provision` daemon either creates, or relies on indirectly,
during the provisioning process.

.. _boot-loader-images:

Boot loader images
------------------

These images must be supplied by the Beaker administrator and copied into the
TFTP root directory manually (with the exception of :file:`pxelinux.0`).
The Cobbler project provides `pre-compiled binaries of common boot loaders
<https://github.com/cobbler/cobbler.github.com/tree/master/loaders>`__. Many
Linux distributions also package these boot loaders.

When Beaker provisions a system it creates a symlink
:file:`bootloader/{fqdn}/image` pointing to one of these images,
depending on the value of the ``netbootloader=`` kernel option
(see :ref:`kernel-options`). Alternatively, the DHCP boot filename
option can be hard-coded to point at one of these images (see
:ref:`adding-systems`).


:file:`pxelinux.0`
    Recommended location of the PXELINUX image, used for x86-based systems with
    BIOS firmware. PXELINUX is a network boot loader developed as part of the
    Syslinux_ project.

    If this file does not exist, Beaker copies the PXELINUX image from the
    Syslinux package to this location so that x86 BIOS systems can be
    provisioned out of the box.

:file:`grub/grub.efi`
    Recommended location of the EFI GRUB_ image, used for x86-based systems
    with UEFI firmware.

:file:`yaboot`
    Location of the Yaboot_ image, used for PowerPC systems.

:file:`elilo-ia64.efi`
    Location of the ELILO_ image, used for IA64 systems.

:file:`aarch64/bootaa64.efi`
    Location of the GRUB2 boot loader image for 64-bit ARM systems.

:file:`boot/grub2/powerpc-ieee1275`
    Location of the GRUB2 boot loader and supporting files for PowerPC
    (PPC64) systems.

.. _Syslinux: http://www.syslinux.org/
.. _GRUB: http://www.gnu.org/software/grub/
.. _ELILO: http://elilo.sourceforge.net/
.. _Yaboot: http://yaboot.ozlabs.org/

.. _boot-loader-configs:

Boot loader configuration directory
-----------------------------------

.. versionadded:: 20

When Beaker provisions a system, it creates a subdirectory
:file:`bootloader/{fqdn}` under the TFTP root directory containing the
following files.

:file:`bootloader/{fqdn}/image`
     Symlink to the desired netboot loader image, as specified in the
     ``netbootloader=`` kernel option.

:file:`bootloader/{fqdn}/etc/{0a010203}`
     Configuration for Yaboot.

:file:`bootloader/{fqdn}/grub.cfg-{0A010203}`
     Configuration for GRUB2 (used by 64-bit ARM and PowerPC systems).

:file:`bootloader/{fqdn}/grub.cfg`
     Default configuration for GRUB2 (used by 64-bit ARM systems).

:file:`bootloader/{fqdn}/petitboot.cfg`
      Configuration for Petitboot.

:file:`bootloader/{fqdn}/pxelinux.cfg/{0A010203}`
      Configuration for PXELINUX.

:file:`bootloader/{fqdn}/pxelinux.cfg/default`
      Default configuration for PXELINUX.

:file:`bootloader/{fqdn}/ipxe/{0a010203}`
      Configuration for iPXE.

:file:`bootloader/{fqdn}/ipxe/default`
      Default configuration for iPXE.

Legacy boot loader configuration files
--------------------------------------

Beaker also creates the following boot loader configuration files for
compatibility reasons. These locations will be used when a system's
DHCP configuration specifies a hard-coded boot filename instead of
using Beaker's configurable netboot loader support.

:file:`pxelinux.cfg/{0A010203}`
    Configuration for PXELINUX. The filename is the IPv4 address of the test
    system, represented as 8 hexadecimal digits (using uppercase letters).

:file:`ipxe/{0a010203}`
    Configuration for iPXE. The filename is the IPv4 address of the test
    system, represented as 8 hexadecimal digits (using lowercase letters).

:file:`grub/images`
    Symlink to the :file:`images` directory.

:file:`grub/{0A010203}`
    Configuration for EFI GRUB. The filename follows the PXELINUX naming
    convention.

:file:`ppc/{0a010203}`
    Symbolic link to the Yaboot image. The filename is the IPv4 address of the
    test system, represented as 8 hexadecimal digits (using lowercase letters).

:file:`etc/{0a010203}`
    Configuration for Yaboot. The filename matches the boot loader symlink
    filename.

:file:`bootloader/{fqdn}/petitboot.cfg`
    Configuration for petitboot.

:file:`ppc/{0a010203}-grub2`
    Symbolic link to the GRUB2 boot loader. The filename is prefixed
    with the IPv4 address of the test system, represented as 8
    hexadecimal digits (using lowercase letters).

:file:`ppc/grub.cfg-{0A1043DE}`; :file:`boot/grub2/grub.cfg-{0A1043DE}`; :file:`grub.cfg-{0A1043DE}`
    Configuration for GRUB2 for PowerPC (PPC64) systems. The filename
    is suffixed with the IPv4 address of the test system, represented
    as 8 hexadecimal digits (using uppercase letters).

:file:`{0A010203}.conf`
    Configuration for ELILO. The filename follows the PXELINUX naming
    convention.

:file:`arm/empty`
    An empty file.

:file:`arm/pxelinux.cfg/{0A010203}`
    Configuration for 32-bit ARM systems. The filename follows the PXELINUX
    naming convention.

:file:`aarch64/grub.cfg-{0A010203}`
    Configuration for 64-bit ARM systems.

:file:`s390x/s_{fqdn}`; :file:`s390x/s_{fqdn}_parm`; :file:`s390x/s_{fqdn}_conf`
    Configuration files for System/390 virtual machines using "zPXE" (Cobbler's
    ``zpxe.rexx`` script).

Other files in the TFTP root directory
--------------------------------------

:file:`images/{fqdn}/`
    Kernel and initrd images for the distro being provisioned. All the
    generated boot loader configurations point at the images in this
    directory.

:file:`pxelinux.cfg/default`
    Default configuration used by PXELINUX when no system-specific
    configuration exists.

    The Beaker administrator can customize this configuration, however it must
    fall back to booting the local disk by default (perhaps after a timeout)
    using the ``localboot 0`` command.

    If this file does not exist, Beaker populates it with a simple default
    configuration that immediately boots the local disk.

:file:`ipxe/default`
    Default configuration available for chain loading by iPXE when no
    system-specific configuration exists.

    The Beaker administrator can customize this configuration; however, it must
    fall back to booting from the local disk by default (perhaps after a timeout)
    using either ``exit``, ``sanboot``, or whatever works most reliably for
    the systems involved.  Note that if a script is chain loaded, it will
    return if that script exits, It may be preferable to allow the called
    script to perform a boot from local disk by following the
    ``chain`` command with an ``exit``.

    If this file does not exist, Beaker populates it with a simple default
    configuration that immediately boots from the local disk.

:file:`aarch64/grub.cfg`
    Default configuration used by 64-bit ARM systems when no system-specific
    configuration exists.

    The Beaker administrator can customize this configuration, however it
    should exit after a timeout using the ``exit`` command.

    If this file does not exist, Beaker populates it with a simple default
    configuration that immediately exits.

:file:`ppc/grub.cfg`
    Default configuration used by PowerPC systems when no system-specific
    configuration exists.

    The Beaker administrator can customize this configuration, however it
    should exit after a timeout using the ``exit`` command.

    If this file does not exist, Beaker populates it with a simple default
    configuration that immediately exits.


:file:`pxelinux.cfg/beaker_menu`
    Menu configuration generated by :program:`beaker-pxemenu` for the
    ``menu.c32`` program (part of Syslinux). See :ref:`pxe-menu` for details.

:file:`ipxe/beaker_menu`
    Menu configuration generated by :program:`beaker-pxemenu` for the
    iPXE scripts.  Chain load this to get the full beaker install menu.

:file:`grub/efidefault`
    Menu configuration generated by :program:`beaker-pxemenu` for EFI GRUB.

:file:`aarch64/beaker_menu.cfg`
    Menu configuration generated by :program:`beaker-pxemenu` for 64-bit ARM
    systems.

:file:`boot/grub2/grub.cfg`
    Default configuration for GRUB2 used by x86 EFI systems when no system-specific
    configuration exists.

    The Beaker administrator can customize this configuration, however it
    should exit after a timeout using the ``exit`` command.

    If this file does not exist, Beaker populates it with a simple default
    configuration that immediately exits.

:file:`boot/grub2/beaker_menu_x86.cfg`
    Menu configuration file generated by :program:`beaker-pxemenu` for EFI GRUB2.
    Menu contains only x86_64 distros.

:file:`boot/grub2/beaker_menu_ppc64.cfg`
    Menu configuration file generated by :program:`beaker-pxemenu` for EFI GRUB2.
    Menu contains only ppc64 distros.

:file:`boot/grub2/beaker_menu_ppc64le.cfg`
    Menu configuration file generated by :program:`beaker-pxemenu` for EFI GRUB2.
    Menu contains only ppc64le distros.

:file:`distrotrees/`
    Cached images for the generated menus. The contents of this directory are
    managed by :program:`beaker-pxemenu`.
