System requirements
===================

There are separate system requirements for the Beaker server and target
hosts. Due to the large number of test files that users can store in the
database, Beaker requires a multiple terabyte disk storage system.

Your Beaker server should have:

-  Red Hat Enterprise Linux 7.8 or higher.

-  200 or more gigabytes hard disk space.

-  4 or more gigabytes of RAM.

-  4 or more CPUs running at 2.5GHz or higher.

-  2 or more terabytes tree storage requirement.

.. note:: If your site already has an existing repository of Red Hat install
   trees, you do not have to meet the tree storage requirement above.

Your target hosts are required to have:

-  Network connectivity to a system running a DHCP server.

-  Network booting capability (like PXE or Netboot).

-  Serial console logging support using a Target Host's management
   adapter or a terminal server such as the Avocent ACS series.

-  KVM support.

Your target hosts also need to include a power controller. Here are some the
most common compatible controllers that are available:

-  HP iLO

-  Dell DRAC

-  WTI Boot bars

-  IPMI 1.5 (or higher)

-  APC

You may mix and match any of these controllers on the target hosts, but
you must include at least one compatible controller per system. Beaker supports
the cman package's fence component. Beaker supports any device that you control
from the Red Hat Enterprise Linux 7 command line.
