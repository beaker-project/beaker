Customizing the installation
============================

Beaker provides a number of ways to customize the distro installation which 
happens at the start of each recipe.

.. todo::

   Describe other ways of customizing the installation, including custom 
   kickstart templates, ks= arg, admin snippets,...

.. _install-options:

Install options
---------------

In Beaker, install options are a set of three related argument strings in the 
form ``foo=bar baz=qux``. Kernel options are passed on the kernel command line 
when the installer is booted. Post-install kernel options (labelled 
:guilabel:`Kernel Options Post` in the web UI) are set in the boot loader 
configuration, to be passed on the kernel command line *after* installation. 
Kickstart metadata variables are passed to the kickstart template engine, and 
can be used to control the content of the kickstart in various ways.

All three options can be set:

* by administrators at the OS version and distro tree levels
  (see :ref:`admin-os-versions`)
* by system owners on a per-system basis (see :ref:`system-details-tabs`)
* by job submitters in each individual recipe (see :ref:`job-workflow-details`)

Beaker combines all the install options in the order listed above to determine 
the effective install options for each recipe.

.. todo::

   Describe syntax of the options, rules for parsing/unparsing, and how 
   combining/overriding works.

.. _kernel-options:

Kernel options
~~~~~~~~~~~~~~

Most kernel options are passed as-is on the kernel command line when the 
installer is booted.
Refer to the distro documentation for details about kernel options supported by 
the installer.

The following kernel options are treated specially by Beaker:

``initrd=<tftp path>``
    Extra initrd/initramfs image to load, in addition to the initrd image for 
    the distro installer. Use this to apply updates to the installer image, or 
    to supply additional drivers for installation.

    If the boot loader supports multiple initrd images, Beaker extracts the 
    ``initrd=`` option from the kernel command line and appends it to the boot 
    loader configuration.

``devicetree=<tftp path>``
    Alternate device tree binary to load. Use this to supply a different device 
    tree binary than the one built into the kernel.

    If the boot loader supports passing a device tree to the kernel (currently 
    only GRUB for AArch64), Beaker extracts the ``devicetree=`` option from the 
    kernel command line and appends it to the boot loader configuration.

.. _kickstart-metadata:

Kickstart metadata
~~~~~~~~~~~~~~~~~~

The following variables are supported. In many cases, these variables 
correspond to the similarly-named kickstart option.

``auth=<authentication configuration options>``
    Authentication configuration to use. For example,
    ``auth='--enableshadow --enablemd5'``. See
    :manpage:`authconfig(8)` to learn more.

``autopart_type=<fstype>``
    Partioning scheme for automatic partitioning (must be one of ``lvm``,
    ``btrfs``, ``plain`` and ``thinp``). On supported distros, it is
    passed as ``--type <fstype>`` to the  ``autopart`` kickstart
    command. On distros where ``autopart`` does not support the
    ``--type`` option, this is ignored.

``beah_rpm=<pkgarg>``
    Name of the Beah RPM to be installed. The value can be any package 
    specification accepted by yum (for example it can include a version, such 
    as ``beah-0.6.48``). The default is ``beah`` which installs the latest 
    version from the harness repos. This variable has no effect when using 
    alternative harnesses.

``beah_no_ipv6``
    If specified, Beah will function in IPv4 only mode even if IPv6
    connectivity is possible.

``dhcp_networks=<device>[;<device>...]``
    Configure additional network devices to start on boot with DHCP activation. 
    The device should be given as a kernel device name (for example, ``em1``) 
    or MAC address.

    Note that the network device used for installation is always set to start 
    on boot with DHCP activation.

``ethdevices=<module>[,<module>...]``
    Comma-separated list of network modules to be loaded during installation.

``firewall=<port>:<protocol>[,<port>:<protocol>...]``
    Firewall ports to allow, for example ``firewall=imap:tcp,1234:ucp,47``. If 
    this variable is not set, the firewall is disabled.

``fstype``
    Filesystem type for all filesystems. Default is to allow the installer to 
    choose.

``grubport=<hexaddr>``
    Hex address of the I/O port which GRUB should use for serial output. If 
    this variable is set, the value will be passed to the ``--port`` option of 
    the ``serial`` command in the GRUB configuration. Refer to `serial in the 
    GRUB manual <http://www.gnu.org/software/grub/manual/grub.html#serial>`__.

``ignoredisk=<options``
    Passed directly to the ``ignoredisk`` kickstart command. Use this to select 
    or omit certain disks for the installation, for example 
    ``ignoredisk=--only-use=sda``.

``keyboard=<layout>``
    Keyboard layout to use. Default is ``us``.

``lang=<localeid>``
    Locale to use. Default is ``en_US.UTF-8``.

``manual``
    Omits most kickstart commands, causing Anaconda to prompt for details. The 
    effect is similar to booting from install media with no kickstart. 
    Typically it is also necessary to set ``mode=vnc``. For systems with
    console log monitoring enabled, it will also be necessary to switch off
    :ref:`installation failure monitoring
    <disable-install-failure-detection>`.

``method=<method>``
   Installation method to use. Default is ``nfs``, supported alternatives
   include ``http`` and ``nfs+iso``. The specific installation methods
   supported for a particular distro tree in a particular lab will depend on
   how the distro was imported into Beaker. The available methods can be
   determined through the web UI by looking at the URL schemes listed for
   the distro tree.

``mode=<mode>``
    Installation mode to use. Valid values are ``text`` (curses-like 
    interface), ``cmdline`` (plain text with no interaction), ``graphical`` 
    (local X server), and ``vnc`` (graphical interface over VNC). The default 
    mode is either ``text`` or ``cmdline``, depending on arch and distro.

``no_<type>_repos``
    Omits repos of the given type. Valid types include ``variant``, ``addon``, 
    ``optional``, and ``debug``. You can find which repo types are available 
    for a particular distro tree under the :guilabel:`Repos` tab on the distro 
    tree page.

``no_updates_repos``
    Omits the fedora-updates repo for Fedora. Note that fedora-updates will 
    still be enabled after installation, this configuration is supplied by the 
    distro and Beaker does not control it.

``no_clock_sync``
    Omits additional packages and scripts which ensure the system clock is 
    synchronized after installation.

``packages=<package>:<package>``
    Colon-separated list of package names to be installed during provisioning. 
    If this variable is set, it replaces any packages defined by default in the 
    kickstart templates. It also replaces any packages requested by the recipe, 
    including task requirements.

    In a recipe, considering using the ``<package/>`` element instead. This 
    augments the package list instead of replacing it completely.

``password=<encrypted>``
    Root password to use. Must be encrypted in the conventional 
    :manpage:`crypt(3)` format.

``remote_post=<url>``
    Specify a URL to a script to be executed post-install. The script must specify a
    interpreter using the ``#!`` line if not a bash script. This is especially useful
    for systems set to Manual mode. If you are scheduling a job, a
    simpler alternative is to embed a ``%post`` scriptlet directly in your
    job XML using the ``<ks_append/>`` element.

``rootfstype``
    Filesystem type for the root filesystem. Default is to allow the installer 
    to choose.

``scsidevices=<module>[,<module>...]``
    Comma-separated list of SCSI modules to be loaded during installation.

``selinux=<state>``
    SELinux state to set. Valid values are ``--disabled``, ``--permissive``, 
    and ``--enforcing``. Default is ``--enforcing``.

``skipx``
    Do not configure X on the installed system. This is needed for headless 
    systems which lack graphics support.

``static_networks=<device>,<ipv4_address>[;...]``
    Configure one or more network devices to start on boot with static IPv4 
    addresses. The device should be given as a kernel device name (for example, 
    ``em1``) or MAC address. The IPv4 address should be given with its netmask 
    in CIDR notation (for example, ``192.168.99.1/24``).

    Note that the network device used for installation is always set to start 
    on boot with DHCP activation.

``timezone=<tzname>``
    Time zone to use. Default is ``America/New_York`` unless overridden by the 
    administrator.
