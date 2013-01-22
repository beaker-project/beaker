How do I…?
==========

This section provides pointers for resolving common administrative problems and 
tasks in Beaker.

… set install options for an entire OS major version?
-----------------------------------------------------

Sometimes you may want to apply install options to all distro trees for a given 
OS major version, without explicitly setting the options every time you import 
a distro tree. For example, as of Fedora 18 Anaconda added a new boot option 
``serial`` which makes it copy install-time console settings to the installed 
system. If your Beaker site is using serial consoles you may want to add 
``serial`` to the kernel options for every Fedora 18 installation. You can do 
that by editing the install options for that OS major version from the "OS 
Versions" page. See :ref:`admin-os-versions`.
