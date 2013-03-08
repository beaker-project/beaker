Support for unsupported_hardware command
========================================

You can now set ``unsupported_hardware`` in kickstart metadata to provision systems with Red Hat
Enterprise Linux 6 on unsupported hardware. It can be set on a
per-system basis in the Install Options tab (see :ref:`system-details-tabs`) or in the
``ks_meta`` attribute of the ``recipe`` element (see :ref:`recipes`).

Beaker will automatically add the ``unsupported_hardware``
command to the kickstart and provision the system, avoiding the need
for manual user intervention during installation.

Related bug: :issue:`907636`
