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

Kickstart metadata
~~~~~~~~~~~~~~~~~~

The following variables are supported. In many cases, these variables 
correspond to the similarly-named kickstart option.

``ethdevices=<module>[,<module>...]``
    Comma-separated list of network modules to be loaded during installation.

``firewall=<port>:<protocol>[,<port>:<protocol>...]``
    Firewall ports to allow, for example ``firewall=imap:tcp,1234:ucp,47``. If 
    this variable is not set, the firewall is disabled.

``fstype``
    Filesystem type for all filesystems. Default is to allow the installer to 
    choose.

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
    Typically it is also necessary to set ``mode=vnc``.

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

``password=<encrypted>``
    Root password to use. Must be encrypted in the conventional 
    :manpage:`crypt(3)` format.

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

``timezone=<tzname>``
    Time zone to use. Default is ``America/New_York`` unless overridden by the 
    administrator.
