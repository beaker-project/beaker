Virtualization workflow
-----------------------

The virtualization testing framework in Beaker utilizes libvirt tools,
particularly virt-install program to have a framework abstracted from
the underlying virtualization technology of the OS. The crux of
the virtualization test framework is a :term:`guest recipe`. Each virtual machine is
defined in its own ``<guestrecipe/>`` element and the guest recipes are a
part of the host's recipe. To illustrate, let's say, we would like to
create a job that will create a host and 2 guests, named guest1 and guest2
respectively. The skeleton of the recipe will look like this::

    <recipe>
            ...
 
            <guestrecipe guestname=guest1 ...>
              ...
              (guest1 test recipe)
              ...
            </guestrecipe>
            <guestrecipe guestname=guest2 ...>
              ...
              (guest2 test recipe)
              ...
            </guestrecipe>
           ...
    </recipe>

Here is a complete job description corresponding to the above skeleton:

.. literalinclude:: virtualization-workflow-sample-job.xml

The above job sets up two guest systems ``guest1`` and ``guest2``
and runs the ``/distribution/check-install`` task in each of them to
indicate whether or not the installation worked and upload the
relevant log files.

Anything that can be described inside a recipe can also be described
inside a guest recipe. This allows the testers to run any existing Beaker
test inside the guest just like it'd be run inside a baremetal machine.

.. admonition:: Guest console logging

   The contents of the guest's console log depends on what Operating System the
   host is running. Anything from Red Hat Enterprise Linux 5 (or equivalent)
   and up (except 5.3) will log the console output from the start of
   installation. Earlier versions will not.

   If the guest is running Red Hat Enterprise Linux 6, the console logging
   will be directed to both ttyS0 and ttyS1

When Beaker encounters a guestrecipe it does create an environmental
variable to be passed on to virtinstall test. The tester-supplied
elements of this variable all come from the guestrecipe element.
Consequently, it's vital that the tester fully understand the properties
of this element. guestrecipe element guestname and guestargs elements.
guestname is the name of the guest you would like to give and is
optional. If you omit this property then the Beaker will assign the
hostname of the guest as the name of the guest. guestargs is where you
define your guest. The values given here will be same as what one would
pass to virt-install program with the following exceptions:

-  Name argument must not be passed on inside guestargs. As mentioned
   above, it should be passed with guestname property..

-  Other than name , -mac, -location, -cdrom (-c) , and -extra-args ks=
   must not be passed. Beaker does those based on distro information
   passed inside the guestrecipe.

-  In addition to what can be passed to virt-install, extra arguments
   -lvm or -part or -kvm can also be passed to guestargs, to indicate
   lvm-based or partition- based guests or kvm guests (instead of xen
   guests).

-  If neither one of -lvm or -part options are given, then a filebased
   guest will be installed. If -kvm option is not given then xen guests
   will be installed. See below for lvm-,partition-based guests section
   for more info on this topic.

-  The virtinstall test is very forgiving for the missed arguments,
   it'll use some default when it can. Currently these arguments can be
   omitted:

   -  -ram or -r , a default of 512 is used

   -  1.-nographics or -vnc, if the guest is a paravirtualized guest,
      then -nographics option will be used, if the guest is an hvm
      guest, then -vnc option will be used.

   -  1.-file-size or -s, a default of 10 will be used.

   -  -file or -f, if the guest is a filebased guest, then the default
      will be /var/lib/xen/images/${guestname}.img . For lvm-based and
      block-device based guest, this option MUST be provided.

KVM vs. Xen guests
~~~~~~~~~~~~~~~~~~

Starting with RHEL 5.4, both Xen and KVM hypervisors are shipped with
the distro. To handle this situation, guest install tests take an extra
argument (-kvm) to identify which type of guests will be installed. By
default, kernel-xen kernel is installed hence the guests are Xen guests.
If -kvm is given in the guestargs, then the installation program decides
that kvm guests are intended to be tested, so boots into the base kernel
and then installs the guests. There can only be one hypervisor at work
at one moment, and hence the installation test expects them all to be
either kvm or xen guest, but not a mix of both.

Dynamic partitioning/LVM
~~~~~~~~~~~~~~~~~~~~~~~~

*Telling Beaker to create partitions/lvm*.
On Beaker, each machine has its own kickstart for each OS family it
supports. In it the partitioning area is marked so that it can be
overwritten to allow having dynamic partitions/lvms in your tests.

The easiest way to specify dynamic partitions is to use the xml workflow
and specify it in your xml file. Syntax of the partition tags is below::

    <partition
      type = type                  <!- required ->
      name = name                  <!- required ->
      size = size in GB            <!- required ->
      fs   = filesystem to format  <!- optional, defaulted to ext3 ->
    </>

<partitions> is the xml element that holds all partition elements.

-  <partition> is the xml element for the partitioning. You can have
   multiple partition elements in a partitions element. It has type,
   name, size and fs text contents all of which except for fs is
   required. Detailed information for each are:

   -  *type*: Type of partition you'd like to use. This can be either
      part of lvm .

   -  *name*: If the type is part, then this will be the mount point of
      the partition. For example, if you would like the partition to be
      mounted to /mnt/temppartition then just put it in here. For the
      lvm type, this will be the name of the volume and all custom
      volumes will go under its own group, prefixed with
      TestVolumeGroup? . For example, if you name your lvm type as
      "mytestvolume", it's go into /TestVolumeGroup??/mytestvolume.

   -  *size*: The size of the partition or volume in GBs .

   -  *fs*:This will be the filesystem the partition will be formatted
      in. If omitted, the partition will be formatted with ext3. By
      default, anaconda mounts all partitions. If you need the partition
      to be unmounted at the time of the test, you can use the
      blockdevice utility which is a test that lives on
      /distribution/utils/blockdevice . This test unmounts the specified
      partitions/volumes and lets users manage custom partitions thru
      its own scripts.

Dynamic partitioning from your workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are using a different workflow and would like to add dynamic
partitioning capability, you can do it by utilizing addPartition() call
to the recipe object. An example can be :

::

         rec = BeakerRecipe()
         # create an ext3 partition of size 1 gig and mount it on /mnt/block1
         rec.addPartition(name='/mnt/block1', type='part', size=1)
         # create an lvm called mylvm with fs ext3 and 5 gig size
         rec.addPartition(name='mylvm', type='lvm', size=5)
         # change the default fs from ext3 to ext4
         rec.addPartition(name='/mnt/block4ext4', type='part', fs='ext4dev', size=1)
         # create an lvm but change the default fs from ext3 to ext4.
         rec.addPartition(name='mylvm4ext4', type='lvm', fs='ext4dev', size=5)

Helper programs installed with Virtinstall
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Virtinstall test also installs a few scripts that can later on be
utilized in the tests. These are completely non-vital scripts, provided
only for convenience to the testers.

*guestcheck4up*:

-  Usage: guestcheck4up <guestname>

-  Description: checks whether or not the guest is live or not.

-  Returns: 0 if guest is not shutoff, 1 if it is.

*guestcheck4down*:

-  Usage: guestcheck4down <guestname>

-  Description: checks whether or not the guest is live or not.

-  Returns: 0 if guest is shutoff, 1 if it is not.

*startguest*:

-  Usage: startguest <guestname> [timeout]

-  Description: Starts a guest and makes sure that it's console is
   reachable within optional $timeout seconds. If timeout value is
   omitted the default is 300 seconds.

-  Returns: 0 if the guest is started and a connection can be made to
   its console within $timeout seconds, 1 if it can't.

*stopguest*:

-  Usage: stopguest <guestname> [timeout]

-  Description: stops a guests and waits for shutdown by waiting for the
   "System Halted." string within the optional $timeout seconds. If
   timeout is omitted , then the default is 300 seconds.

-  Returns: 0 if the shutdown was successful, 1 if it wasn't.

*getguesthostname*:

-  Usage: getguesthostname <guestname>

-  Returns: A string that contains the hostname of the guest if
   successful, or an error string if it's an error.

*wait4login*:

-  Usage: wait4login <guestname> [timeout]

-  Description: It waits until it gets login: prompt in the guest's
   console within $timeout seconds. If timeout argument is not given,
   it'll wait indefinitely, unless there is an error!

-  Returns: 0 on success , or 1 if it encounters an error.

*fwait4shutdown:*

-  Usage: wait4shutdown <guestname> [timeout]

-  Description: It waits until it gets shutdown message in the guest's
   console within $timeout seconds. If timeout argument is not given,
   it'll wait indefinitely, unless there is an error!

-  Returns: 0 on success , or 1 if it encounters an error.
