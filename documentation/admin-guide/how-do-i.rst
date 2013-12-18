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


… update the inventory details for a system?
--------------------------------------------

The inventory details for a system are gathered automatically using the
:ref:`inventory-task` task. The easiest way to run this task is to use the
``machine-test`` workflow to generate and submit an appropriate job
definition::

    bkr machine-test --inventory --family=RedHatEnterpriseLinux6 \
         --arch=x86_64 --machine=<FQDN>

Refer to :ref:`bkr-machine-test` for more details.


… store my log files somewhere other than the lab controller?
-------------------------------------------------------------

Beaker has the option of moving it's log files from the default
location of the lab controller, to a remote archive server, via rsync.

If your primary aim in using the archive server is to free up space
on the lab controller, mounting a file system backed by bulk storage
may be a better solution. However if this is not a preferred option,
and if the size of Beaker's job logs files exceeds the storage available to your
lab controllers, or if you need to centralize log storage for administrative
reasons, an :ref:`archive server <architecture-archive-server>` may be a suitable approach.

