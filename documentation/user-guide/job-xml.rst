Job XML
-------

You can specify Beaker jobs using an XML file. This allows users a more
consistent, maintainable way of storing and submitting jobs. You can
specify and save entire jobs, including many recipes and recipe sets in
them in XML files and save them as regression test suites and such.

The various elements along with their attributes and the values they can
take are described in the RELAX NG schema described in the file
`beaker-job.rng <http://beaker-project.org/schema/beaker-job.rng>`_. 

.. _job-workflow-details:

Job workflow details
''''''''''''''''''''
There are various XML entities in the job definitions created for a
workflow. Each job has a root node called the job element:

::

    <job>
    </job>

A direct child is the "whiteboard" element. The content is normally a
mnemonic piece of text describing the job:

::

    <job>
    <whiteboard>
            Apache 2.2 test
    </whiteboard>
    </job>

The next element is the "recipeSet" (which describes a recipe set. See
:ref:`recipes` for full details). A job workflow can have one or
more of these elements, which contain one or more "recipe" elements.
Whereas tasks within a recipe are run in sequence on a single system,
all recipes within a recipe set are run simultaneously on systems
controlled by a common lab controller. This makes recipe sets useful for
scheduling multihost jobs, where recipes playing different roles (e.g.
client, server) run concurrently on separate systems.

When multiple recipe sets are defined in a single job, they are run in
no predetermined order, are not necessarily scheduled concurrently and
may run on systems controlled by different lab controllers. The
advantage of combining them into one job is that they will report a
single overall result (as well as a result for each recipe set) and can
be managed (e.g. submitted, cancelled) as a single unit.

::

    <job>
      <whiteboard>
        Apache 2.2 test
      </whiteboard>
        <recipeSet>
        </recipeSet>
    </job>

As noted above, the "recipeSet" element contains "recipe" elements.
Individual recipes can have the following attributes

-  "kernel\_options"

   -  **vnc** Setting this will do a vnc install

-  "kernel\_options\_post"

-  "ks\_meta"

   -  **manual** minimal kickstart, should also use mode=vnc

   -  **mode=text\|cmdline\|graphical\|vnc** Specify what mode to use
      for install, default is either text or cmdline

   -  **firewall=port:protocol<,port:protocol>** Default is firewall
      disabled, Example: firewall=imap:tcp,1234:ucp,47

   -  **keyboard=us** Specify Keyboard, Default is us

   -  **lang=en\_US.UTF-8** Specify install language, Default is
      en\_US.UTF-8

   -  **password=<encrypted>** Override default password value, must be
      encrypted

   -  **selinux=--enforcing** Selinux is enabled by default, --disabled
      or --permissive are valid choices

   -  **timezone=America/New\_York** TimeZone to use, default to
      America/New\_York

   -  **scsidevices=qla2xxx,megaraid\_mbox** Only load these scsi
      modules if set

   -  **ethdevices=tg3,e1000** Only load these network modules if set

   -  **no\_TYPE\_repos** If this option is specified it will omit repos
      of TYPE from the kickstart, TYPE can be one of debug, optional,
      adddon or variant. You can see the different types of repos
      available for a distro on the /distrotrees page under the repo
      tab.

   -  **skipx** Do the install without setting up graphics. This is
      needed for headless systems.

   -  **ignoredisk** Use this to ignore certain disks for install. For
      example: ignoredisk=--only-use=sda

   -  **rootfstype** Specifies root filesystem type

   -  **fstype** Specifies filesystem type for all volumes

-  **role** In a Multihost environment, it could be either ``SERVERS``,
   ``CLIENT`` or ``STANDALONE``. If it is not important, it can be
   ``None``.

-  **whiteboard** Text that describes the Recipe

Here is an example::

    <job>
      <whiteboard>
        Apache 2.2 test
      </whiteboard>
        <recipeSet>
          <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="Lab Controller">
          </recipe>
        </recipeSet>
    </job>

.. admonition:: Avoid having many recipes in one recipe set

   Because recipes within a recipe set are required to run simultaneously,
   no recipe will commence execution until all other sibling recipes are
   ready. This involves each recipe reserving a system, and waiting until
   every other recipe has also reserved a system. This can tie up resources
   and keep them idle for long amounts of time. It is thus worth limiting
   the recipes in each recipe set to only those that actually need to run
   simultaneously (i.e multihost jobs)

Within the ``recipe`` element, you can specify what packages need to be
installed on top of anything that comes installed by default.

::

    <job>
      <whiteboard>
        Apache 2.2 test
      </whiteboard>
        <recipeSet>
          <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="Lab Controller">
            <packages>
              <package name="emacs"/>
              <package name="vim-enhanced"/>
              <package name="unifdef"/>
              <package name="mysql-server"/>
              <package name="MySQL-python"/>
              <package name="python-twill"/>
                            </packages>
          </recipe>
        </recipeSet>
    </job>

If you would like you can also specify your own repository that provides
extra packages that your job requires. Use the ``repo`` tag for this.
You can use any text you like for the name attribute.

::

    <job>
     <whiteboard>
        Apache 2.2 test
      </whiteboard>
        <recipeSet>
          <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="Lab Controller">
            <packages>
             <package name="emacs"/>
              <package name="vim-enhanced"/>
              <package name="unifdef"/>
              <package name="mysql-server"/>
              <package name="MySQL-python"/>
              <package name="python-twill"/>
            </packages>

            <repos>
              <repo name="myrepo_1" url="http://my-repo.com/tools/beaker/devel/"/>
            </repos>

          </recipe>
        </recipeSet>
    </job>

To actually determine what distro will be installed, the
``<distroRequires/>`` needs to be populated. Within, we can specify such
things as as ``<distro_arch/>``, ``<distro_name/>`` and
``<distro_method/>``. This relates to the Distro architecture, the name
of the Distro, and it's install method (i.e nfs,ftp etc) respectively.
The ``op`` determines if we do or do not want this value i.e ``=`` means
we do want that value, ``!=`` means we do not want that value.
``<distro_virt/>`` will determine whether we install on a virtual
machine or not.

::

    <job>
      <whiteboard>
        Apache 2.2 test
      </whiteboard>
        <recipeSet>
          <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="Lab Controller">
            <packages>
              <package name="emacs"/>
              <package name="vim-enhanced"/>
              <package name="unifdef"/>
              <package name="mysql-server"/>
              <package name="MySQL-python"/>
              <package name="python-twill"/>
            </packages>

            <repos>
              <repo name="myrepo_1" url="http://my-repo.com/tools/beaker/devel/"/>
            </repos>
            <distroRequires>
              <and>
                <distro_arch op="=" value="x86_64"/>
                <distro_name op="=" value="RHEL5-Server-U4"/>
                <distro_method op="=" value="nfs"/>
              </and>
              <distro_virt op="=" value=""/>
            </distroRequires>
          </recipe>
        </recipeSet>
    </job>

``<hostRequires/>`` has similar attributes to ``<distroRequires/>``

::

    <job>
      <whiteboard>
        Apache 2.2 test
      </whiteboard>
        <recipeSet>
          <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="Lab Controller">
            <packages>
               <package name="emacs"/>
              <package name="vim-enhanced"/>
              <package name="unifdef"/>
              <package name="mysql-server"/>
              <package name="MySQL-python"/>
              <package name="python-twill"/>
            </packages>
            <repos>
              <repo name="myrepo_1" url="http://my-repo.com/tools/beaker/devel/"/>
            </repos>
            <distroRequires>
              <and>

                <distro_arch op="=" value="x86_64"/>
                <distro_name op="=" value="RHEL5-Server-U4"/>
                <distro_method op="=" value="nfs"/>
              </and>
              <distro_virt op="=" value=""/>
            </distroRequires>
            <hostRequires>
              <and>
                <arch op="=" value="x86_64"/>
                <hypervisor op="=" value=""/>
              </and>
            </hostRequires>
          </recipe>
        </recipeSet>
    </job>

.. admonition:: Bare metal vs hypervisor guests

   Beaker supports direct provisioning of hypervisor guests. These hypervisor 
   guests live on non volatile machines, and can be provisioned as a regular 
   bare metal system would. They look the same as regular system entries, 
   except their ``Hypervisor`` attribute is set. If your recipe requires a bare 
   metal machine, be sure to include <hypervisor op="=" value=""/> in your 
   <hostRequires/>

.. _device-specs:

If your recipe requires the presence of a specific device on the host,
you may specify that using the ``<device>`` element (within
``<hostRequires>``) using a syntax such as::

    <device op="=" type="network" />

The above device specification will try to find a host which has a
network card to run your recipe on. If you wanted that the network
card should be from a specific vendor, you would specify it, like so::

    <device op="=" type="network" vendor_id="8086" />

The other possible values of ``type`` include (but are not limited
to): ``cpu``, ``display``, ``scsi``, ``memory`` and ``usb``.
There are a number of other attributes that you can use to specify a device:
``bus``, ``driver``, ``device_id``, ``subsys_vendor_id``,
``subsys_device_id`` and ``description``.

The ``op`` attribute can take one of the four values:``!=``, ``like``,
``==``, ``=``, with the last two having serving the same
functionality. The ``!=, =`` and ``==`` operators should be used when
you want an exact match of your device specification. For example, if
to ask Beaker to run your recipe on a host with *no* USB device, you
would use the following specification::

    <device op="!=" type="USB" />

On the other hand, if you are only partially sure about what the device
specification you are looking for, you would use the ``like``
operator. For example, the following specification will try to find a
host with a graphics controller::

    <device op="like" description="graphics"/>

You can of course combine more than one such ``<device>``
elements. The next example shows an entire ``<hostRequires>`` specification::

    <hostRequires>
      <and>
        <system_type op="=" value="Machine"/>
        <device op="=" type="network" description="Extreme Gigabit Ethernet" />
        <device op="=" type="video" description="VD 0190" />
      </and>
    </hostRequires>

The above specification will try to find a host which is a Machine
with a network interface (with description as "Extreme Gigabit
Ethernet") and with a video device with the description as "VD 0190".

.. admonition:: Inventoried Systems Only

   It is worthwhile to note here that if you submit device
   specifications in your ``<hostRequires>``, Beaker will match the
   specifications against the current inventory data it has for the
   systems. For this data to be available for a system, it is necessary that the
   :ref:`Inventory task <next-steps>` has been run on it at some point of time before
   your job specification has been submitted. What this basically
   means is that unless a system has been inventoried, Beaker won't be
   able to find it, even if it has the particular device you are
   requesting. It may be a good idea to first search if there is any
   system at all with the device you want to run your recipe on. (See:
   :ref:`system-searching`).


All that's left to populate our XML with, are the 'task' elements. The
two attributes we need to specify are the ``name`` and the ``role``.
You can find which tasks are available by :ref:`searching the task library 
<task-searching>`. Also note that we've added in a ``<param/>``
element as a descendant of ``<task/>``. The ``value`` of this will be
assigned to a new environment variable specified by ``name``.

::

    <job>
      <whiteboard>
        Apache 2.2 test
      </whiteboard>
        <recipeSet>
          <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="Lab Controller">
            <packages>
              <package name="emacs"/>
              <package name="vim-enhanced"/>
              <package name="unifdef"/>
              <package name="mysql-server"/>
              <package name="MySQL-python"/>
              <package name="python-twill"/>
            </packages>

            <repos>
              <repo name="myrepo_1" url="http://my-repo.com/tools/beaker/devel/"/>
            </repos>
            <distroRequires>
              <and>
                <distro_arch op="=" value="x86_64"/>
                <distro_name op="=" value="RHEL5-Server-U4"/>
                <distro_method op="=" value="nfs"/>
              </and>
              <distro_virt op="=" value=""/>
            </distroRequires>

            <task name="/distribution/install" role="STANDALONE">
              <params>
                    <param name="My_ENV_VAR" value="foo"/>
               </params>
             </task>

          </recipe>
        </recipeSet>
    </job>

By default, the kickstart fed to Anaconda is a generalized kickstart for
a specific distro major version. However, there are a couple of ways to
pass in a customized kickstart.

One method is to pass the ``ks`` key/value to the ``kernel_options``
parameter of the ``recipe`` element. Using this method the kickstart
will be used by Anaconda unaltered.

::

    <recipe kernel_options='ks=http://example.com/ks.cfg' />

Alternatively, the kickstart can be written out within the ``recipe``
element.

::

    <kickstart>
      install
      key --skip
      lang en_US.UTF-8
      skipx
      keyboard us
      network --device eth0 --bootproto dhcp
      rootpw --plaintext testingpassword
      firewall --disabled
      authconfig --enableshadow --enablemd5
      selinux --permissive
      timezone --utc Europe/Prague

      bootloader --location=mbr --driveorder=sda,sdb
    # Clear the Master Boot Record
      zerombr
    # Partition clearing information
      clearpart --all --initlabel
    # Disk partitioning information
      part /RHTSspareLUN1 --fstype=ext3 --size=20480 --asprimary --label=sda_20GB --ondisk=sda
      part /RHTSspareLUN2 --fstype=ext3 --size=1 --grow --asprimary --label=sda_rest --ondisk=sda
      part /boot --fstype=ext3 --size=200 --asprimary --label=BOOT --ondisk=sdb
    # part swap --fstype=swap --size=512  --asprimary --label=SWAP_007 --ondisk=sdb
      part / --fstype=ext3 --size=1 --grow --asprimary --label=ROOT  --ondisk=sdb

      reboot

      %packages --excludedocs --ignoremissing --nobase
    </kickstart>

When passed a custom kickstart in this manner, Beaker will add extra
entries into the kickstart. These will come from install options that
have been specified for that system, arch and distro combination;
partitions, packages and repos that have been specified in the
``recipe`` element; the relevant snippets needed for running the
harness. For further information on how Beaker processes kickstarts and
how to utilize their templating language, see :ref:`kickstarts`.
