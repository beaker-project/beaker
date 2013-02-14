Disk information in inventory
=============================

The ``/distribution/inventory`` task now collects information about disks 
present in the system and records these in Beaker. The disk information appears 
under the "Details" tab of the system page. You can search disk information in 
the web UI, and you can filter systems by their disks in ``<hostRequires/>`` 
using the ``<disk/>`` element.

Related bug: `766919 <https://bugzilla.redhat.com/show_bug.cgi?id=766919>`_
