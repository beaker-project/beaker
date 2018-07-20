
.. _troubleshooting:

Troubleshooting
---------------

Why is my job aborted earlier than the specified reserve time?
==============================================================

A reason can be the hard limit of **99 hours/4 days** in
``/distribution/reservesys``. Check your job XML if you're trying to reserve the
system for longer. You can also check the result for a warning:
``watchdog_exceeds_limit``. :ref:`system-reserve` describes system reservation
in detail.

How to archive XML file for a job from within a Beaker job?
===========================================================

You can use the :ref:`harness API<harness-http-api>`::

  wget ${BEAKER_LAB_CONTROLLER_URL}recipes/$BEAKER_RECIPE_ID

Troubleshooting checklist for an aborted job
============================================

#. Has the first task in the recipe passed?

    Yes.
        Installation has passed in this case, beaker performed provisioning and test
        harness deployment well. Please check the particular task with failure if it is
        working properly.

    No, Recide ID does not match any systems.
        There isn't any lab containing both requested distribution and requested
        machine. Try to change the requirements of your job and/or order suitable
        hardware.

    No, Command XYZ failed .
        Power management isn't working (machine can't be rebooted/switched
        on/switched off). This error is handled automatically by Beaker - it marks
        the machine as broken and notifies its administrator.

    No, External Watchdog Expired.
        Something went wrong during deployment. Check for status of other tasks in queue.

#. Are all jobs/recipes aborted?

    Yes.
        There is very likely something wrong with Beaker. Report it to your Beaker administrator.

    No.
        Go back to your failed job/recipe and start troubleshooting, check the
        console output first.

#. Is the console output missing/empty?

    .. note:: An empty console.log does not have to be necessarily blank. It can be
              considered *blank* if it contains a few time stamps.

    Yes.
        Either the system is stuck and cannot power on, or its serial console is
        not configured properly. No further diagnostics are possible, report
        this problem to the system owner.

    No.
        Great! Look at the bottom of the console output.

#. Does the bottom of the console output contain errors?

    .. note:: Look carefully for possible causes. Typically, the bottom of an
              aborted job contains a few lines with time stamps and some useful
              information above these lines. This is the last information
              printed. This information can be hard to read as it was part of an
              ncurses dialog utilizing ANSI escape codes. Beaker removes escape
              characters in the console output, but the rest of the sequence
              stays there.

    Yes, there is some problem with:
        * the :ref:`disk space allocation <troubleshooting-partitioning-allocate-partition>`
        * the :ref:`network <troubleshooting-network-issue>`
        * Python traceback from anaconda. Please report a bug to anaconda

    No.
        Check if machine initiated installation at all.

#. Is ksdevice=eth[0-9] set for the machine?

    .. _troubleshooting-ksdevice:

    New RHEL and Fedora distributions use different naming scheme for network
    interfaces based on physical placement. Typically these names look like 'em1' or
    'p3p1'. So far it may happen that beaker inventory defines ksdevice option with
    some traditional ethX name. To check this:

    * look at the NIC name at the bottom of the console output and
    * search for ksdevice= in anaconda.log

    If you see new names in the console output and traditional name as ksdevice, you're affected by this issue.

#. Did the machine boot into an existing installation, instead of running the installer?

    The boot order might have changed on the machine to boot from disk. In this
    case, it will never start the installation. In this case:

    * console.log is the only available log file,
    * the console output contains exclusively output of a boot loader (typically grub) and
      messages of boot from disk, there is no message related to boot from network,
      no message from Anaconda installer.

    In case the installation has started, check result of :ref:`installation of harness <troubleshooting-harness>`.


#. Did the Beaker harness successfully install?

    .. _troubleshooting-harness:

    To check this, open the console output and search for string ``beah``. In case of
    successful installation you will find yum output with successful installation of
    several packages, beah is one of this.

    Some occurrences 'beah' substring were found.
        Check repositories added via kickstart.

    Were all repositories setup properly?
        It may happen that repositories are unavailable. To recognize it open
        the console output and search for string 'Trying other mirror'. If you
        find message informing you about some repomd.xml: [Errno 14] HTTP Error
        404: Not Found then you found it.

    There are some inaccessible repositories.
        Somebody added to a kickstart of your job incorrect path to the repository.
        If you did it (you should know that), please fix.

.. _troubleshooting-network-issue:

Network issue during installation
=================================

If there was an error to configure the network interface, check if the
``ksdevice`` :ref:`value is correct <troubleshooting-ksdevice>`.

.. _troubleshooting-partitioning-allocate-partition:

Error: ``Could not allocate requested partitions``
==================================================

#. First check your job XML. Is ``<hostRequires />`` requesting a system with a
   large enough disk to satisfy the ``<partition />`` you have requested?
#. Check the kernel output to ensure all expected disks and storage controllers
   are present. If any are missing, report a bug against the distro.

   Some storage controllers are unsupported in some distros. For example,
   the ``cciss`` driver was dropped from newer kernels and so any systems using
   an older SmartArray controller cannot be provisioned with RHEL7 or Fedora. In
   this case, the system owner should update the :guilabel:`Excluded Families`
   settings to exclude unsupported distros from their system. Report this
   problem to the system owner.

Error: ``Cannot access /var/run/beah/rhts-compat/launchers: No such file or directory``
=======================================================================================

#. Check the network connection, it is most likely offline.
#. Some kind of installation error occurred, which is *fixed* by rebooting the host.
#. The system is incompatible with rhts-compat, so it must be disabled in the job XML.
