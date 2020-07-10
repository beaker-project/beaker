
.. _adding-systems:

Adding your system to Beaker
============================

To add a system, go to any system search page, then click the :guilabel:`Add` 
button at the bottom of the page. Fill in the system's details and click the 
:guilabel:`Save Changes` button to create a new record for your system. Define 
which architectures your system supports on the :guilabel:`Arches` tab. Then 
fill in the other details as described below.

.. _system-dhcp:

DHCP and DNS
------------

In order to provision the system, Beaker needs to be able to resolve its FQDN 
consistently. The system must have a static IPv4 address assigned by DHCP and 
a matching ``A`` record in DNS which resolves to that address. It is also 
recommended to add a corresponding ``PTR`` record so that reverse hostname 
lookups work correctly on the system after it is provisioned.

If the system has multiple network interfaces, ensure that the MAC address in 
the DHCP reservation matches the network interface which the system's firmware 
boots from.

DHCP option 42 ("NTP servers") must be set, so that the system's clock can be 
synchronized at the start of each recipe. Use a public NTP server if none are 
available in your lab.

The DHCP configuration must also include suitable netboot options for the 
system. Typically DHCP option 66 ("TFTP Server Name") is set to the address of the 
lab controller and option 67 ("Boot File Name") can either be set to
:file:`bootloader/{fqdn}/image` to take advantage of Beaker's custom
netboot loader support or a specific bootloader such as ``pxelinux.0``
(see :ref:`boot-loader-images` and :ref:`boot-loader-configs`).

Power control
-------------

If the system supports remote power control, either through an out-of-band 
management controller or using a switchable power port, configure the details 
on the :guilabel:`Power Config` tab. Virtual machines can use the ``virsh`` 
power type.

.. todo:: refer to docs for power types once they exist

This is a prerequisite for automatic (unattended) provisioning. If the system 
has no remote power control, you will have to reboot it manually when Beaker 
provisions it.

Boot order
----------

For automatic provisioning, you must also configure the system's firmware
to boot from the network first. Beaker will ensure that the system either boots 
an installer image over the network or falls back to booting from the local 
hard disk as appropriate. See :ref:`provisioning-process` for details about how 
automatic provisioning works in Beaker.

Remote console
--------------

If your system supports remote console access (serial-over-LAN or similar), you 
can hook it up to the conserver in your lab. This will allow Beaker to capture 
console logs and detect kernel panics.

.. todo:: refer to docs about setting up conserver once they exist

Install options
---------------

Use the :guilabel:`Install Options` tab to set default install options for your 
system, if necessary. See :ref:`install-options` to learn about these settings. 
Refer to the Anaconda documentation for the available kernel options.

If you have connected the system's serial console to conserver, set the 
``console`` kernel option appropriately. For example, assuming the system's 
serial-over-LAN device appears as the second serial port, set 
``console=ttyS1,115200n8``.

By default Beaker will apply ``ksdevice=bootif`` to the kernel options (this is 
defined in :file:`/etc/beaker/server.cfg`). This setting is suitable for 
x86-based systems booting PXELINUX, but for other systems (including UEFI-based 
systems) which have more than one network interface, you must set the 
``ksdevice`` option explicitly, otherwise Anaconda will prompt for which 
interface to use during installation. If only one network interface has a cable 
connected, you can set ``ksdevice=link``. If more than one interface has 
a cable connected, you must nominate a specific interface to be used for 
installation: ``ksdevice=00:11:22:33:44:55``.  If you want to remove the
Beaker default of ksdevice kernel option, you can precede the option with `!`
within your recipe's setting, i.e, `kernel_options="!ksdevice"`.

Next steps
----------

To test your system's configuration, try provisioning it (see 
:ref:`provisioning-a-system`).
You can watch the provisioning process through the console. Please, be patient. 
The provisioning may take some time.

To populate your system's hardware details in Beaker, you should :ref:`create 
a job <submitting-a-new-job>` to run the Beaker-provided :ref:`inventory-task` 
task on the machine. The easiest way to do this is to use the :ref:`bkr 
machine-test <bkr-machine-test>` command to generate and submit an appropriate 
job definition::

    bkr machine-test --inventory --family=RedHatEnterpriseLinux6 \
         --arch=x86_64 --machine=<FQDN>

Once your system is operational, you may want to use Beaker's :doc:`system 
sharing features <sharing>` to let others use or administer your system.
