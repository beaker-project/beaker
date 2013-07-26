.. _importing-distros:

Importing distros
=================

In order for a distro to be usable in Beaker, it must be "imported". Importing 
a distro into Beaker registers the location(s) from which the distro tree is 
available in the lab, along with various metadata about the distro.

To import a distro, run ``beaker-import`` on the lab controller and pass all 
the URLs under which the distro is available. For example::

    beaker-import \
        http://mymirror.example.com/pub/fedora/linux/releases/17/Fedora/ \
        ftp://mymirror.example.com/pub/fedora/linux/releases/17/Fedora/  \
        nfs://mymirror.example.com:/pub/fedora/linux/releases/17/Fedora/

Distros must be imported separately on each lab controller, and you can import 
from a different set of URLs in each lab. This allows you to import distros 
from the nearest mirror in each lab.

You can check that the distros were added successfully by browsing the Distros 
page (see :ref:`distros`).

.. note:: The Beaker server stores a local copy of the harness packages under 
   ``/var/www/beaker/harness``, arranged as one Yum repo for every distro 
   family. The first time you import a new distro family you will need to run 
   ``beaker-repo-update`` on the server to populate the harness repo for the 
   new distro family.

.. _stable-distro-tagging:

Automated jobs for new distros
------------------------------

Beaker has a facility for running scripts whenever a new distro is imported, 
provided by the ``beaker-lab-controller-addDistro`` package.
After installing that package, scripts placed in the 
``/var/lib/beaker/addDistro.d`` directory will be run each time a distro is 
imported.

Beaker ships with a script, ``/var/lib/beaker/addDistro.d/updateDistro``, which 
schedules a Beaker job to test installation of the new distro and tags it with 
``STABLE`` if the job completes without error. Use this as a guide for creating 
more specific jobs that you might find useful.

.. note:: The ``updateDistro`` script assumes that the Beaker client is 
   correctly configured on the lab controller. See :ref:`installing-bkr-client`.

Generating a PXE menu
---------------------

Beaker includes a command, ``beaker-pxemenu``, which can be run on the lab 
controller to generate a PXELINUX-compatible boot menu listing the distros in 
Beaker. Users in the lab can then perform manual installations by selecting 
a distro from the menu. The menu is written to ``pxelinux.cfg/beaker_menu`` in 
the TFTP root directory.

You can limit the menu to only contain distros tagged in Beaker with a
certain tag, by passing the ``--tag`` option to ``beaker-pxemenu``. By
default, all distros which are available in the lab are included in the
PXE menu.

.. note:: If you have configured a non-default TFTP root directory in 
   ``/etc/beaker/labcontroller.conf``, be sure to pass that same directory in 
   the ``--tftp-root`` option to ``beaker-pxemenu``.

If using the PXE menu, you should configure ``pxelinux.cfg/default`` to
boot from local disk by default, with an option to load the menu. For
example::

    default local
    prompt 1
    timeout 200

    say ***********************************************
    say Press ENTER to boot from local disk
    say Type "menu" at boot prompt to view install menu
    say ***********************************************

    label local
        localboot 0

    label menu
        kernel menu.c32
        append pxelinux.cfg/beaker_menu

If your site imports distros into Beaker infrequently, you may prefer to
run ``beaker-pxemenu`` after importing new distros. Otherwise, you can
create a cron job to periodically update the PXE menu::

    #!/bin/sh
    exec beaker-pxemenu --quiet
