Configurable netboot loader
===========================

Beaker now supports configuring the netboot loader used on a per-job
basis, by passing ``netbootloader=`` in the kernel options. For
example, this allows Beaker to use yaboot when provisioning RHEL7.0
and older distros on ppc64, and GRUB2 when provisioning new
distros. This is however only supported when the DHCP configuration
for the systems have been updated appropriately.

See :ref:`system-dhcp`, :ref:`boot-loader-images`, :ref:`boot-loader-configs` and
:ref:`kernel-options` to learn more.

(Contributed by Amit Saha in :issue:`1156036`)
