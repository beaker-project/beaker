Customizing partitions and volumes
==================================

.. highlight:: xml

When Beaker installs the distro at the start of each recipe, it will use the
default disk layout ("automatic partitioning" with the ``autopart`` kickstart
command).

The installer's automatic partitioning behaviour varies across releases, but
in most cases the installer will assign all available disks to a single LVM
volume group, with a swap volume, a 50GB root volume, and a home volume using
all remaining space. Refer to the installer documentation for details about
the automatic partitioning behaviour in each release.

Adding custom partitions
------------------------

If the automatic partitioning behaviour is not suitable, your recipe can
activate Beaker's custom partitioning logic by passing extra custom partitions
in the ``<partitions/>`` element. For example, this will produce a 25GiB
XFS-formatted filesystem mounted at ``/var/tmp``::

    <recipe>
      ...
      <partitions>
        <partition type="part" name="var/tmp" fs="xfs" size="25" />
      </partitions>
      ...
    </recipe>

Each ``<partition/>`` element represents a custom disk partition and
filesystem which will be created during the installation and then mounted when
the recipe runs. Instead of using the ``autopart`` kickstart command, Beaker
will emit suitable ``part`` commands to produce the desired partition layout.

.. note::

   When Beaker's custom partitioning logic is activated, the root (``/``),
   ``/boot``, and swap volumes are always created. Do not specify custom
   partitions for these.

The ``<partition/>`` element has the following attributes:

``type``
  The default value ``part`` produces a simple hard disk partition containing
  a filesystem directly. The value ``lvm`` instead produces a partition
  containing an LVM physical volume, with a *separate* LVM volume group
  containing a single LVM logical volume containing a filesystem.

``name``
  Mount point of the volume, without leading slash.

``fs``
  Filesystem type which will be used when formatting the partition, for
  example ``ext4``, ``xfs``, or ``btrfs``. This follows the kernel naming
  scheme for filesystems, and the possible values depend on the distro. If
  this attribute is omitted, the installer will use the distro default
  filesystem type.

``size``
  Size of the partition in GiB.

There are also a number of kickstart metadata variables which influence the
behaviour of the custom partitioning logic: ``ondisk``, ``fstype``,
``rootfstype``, and ``swapsize``. Refer to :ref:`kickstart-metadata`. Note
that if your recipe defines any of these variables, the custom partitioning
logic will be applied *even if* your recipe does not contain any
``<partition/>`` elements.

Suppressing ``autopart`` and specifying partitioning commands directly
----------------------------------------------------------------------

You can define the ``no_autopart`` kickstart metadata variable to suppress the
``autopart`` command which Beaker injects into the kickstart by default. If
you *also* avoid all of the above custom partitioning mechanisms described
above, this will result in a kickstart containing *no* partitioning commands.

Normally the installer considers this to be an error, because there are no
instructions about how to lay out the disks.

However you can combine this with a ``<ks_append/>`` element (see
:ref:`ksappend`) to append your own raw partitioning commands directly.
For example, this will produce a 20GiB root volume and the remaining disk space 
will be allocated to a separate volume mounted at ``/var/lib/mysql``, both 
using the default filesystem type for the distro::

    <recipe ks_meta="no_autopart">
      ...
      <ks_appends>
        <ks_append>
    part /boot --recommended
    part / --size=20480
    part /var/lib/mysql --grow
        </ks_append>
      </ks_appends>
      ...
    </recipe>
