BIOS boot partition
===================

Beaker's kickstart templates now define a 1MB "BIOS boot" partition under the 
following circumstances:

* the recipe uses custom partitioning (``<partition/>`` or a related
  kickstart metadata variable)
* the system is x86 with BIOS firmware, or EFI firmware running in BIOS
  compatibility mode
* the distro supports GPT format disks for BIOS systems (Fedora, CentOS 7,
  RHEL 7)

The BIOS boot partition is needed in case the boot disk is larger than 2TB, 
which causes Anaconda to use GPT instead of MBR when formatting the disk.
