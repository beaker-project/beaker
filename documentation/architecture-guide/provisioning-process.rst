
.. _provisioning-process:

Provisioning process
====================

This section describes how Beaker coordinates automatic (unattended) 
provisioning of the systems under its control.

The following sequence of events takes place when Beaker provisions a system:

#. The server generates a unique kickstart.
#. The lab controller writes out a netboot configuration for the system in the 
   TFTP root directory.
#. The lab controller reboots the system.
#. The system firmware should be configured to boot from the network. It boots 
   the images served by the lab controller and starts Anaconda.
#. A post-installation script supplied by Beaker does some extra preparation:

   * checks in with Beaker
   * instructs the lab controller to clear the netboot configuration
   * configures an NTP daemon to ensure the system clock is accurate
   * installs and configures the test harness

#. The system reboots and the harness begins running the Beaker recipe.


.. _boot-order-details:

Boot order
----------

For systems with BIOS-compatible firmware (or other legacy firmware) the boot 
order should always be set to boot from the network first. When the system is 
provisioned it will boot the installer over the network. After installation 
finishes, Beaker clears the system-specific netboot configuration. Then, on the 
next boot, the boot loader will fall back to a default configuration which 
instructs it to boot from the local hard disk instead. This is what allows 
Beaker to automatically provision systems without changing their boot order.

For systems with EFI-compatible firmware, which allows the boot order to be 
changed at runtime from within the operating system, the process is more 
complicated. On these systems, after installation finishes Anaconda dynamically 
creates a new boot entry and adds it to the top of the boot order. 
A post-installation script supplied by Beaker then changes the boot order back 
so that netboot is at the top, and also sets the ``BootNext`` variable so that 
on next boot the local hard disk is used instead. The :program:`rhts-reboot` 
script also sets ``BootNext`` to boot locally. In this way, the system will 
continue to boot from the hard disk until the current recipe is finished. After 
that the system will revert to booting from the network, allowing Beaker to 
provision it for the next recipe.
