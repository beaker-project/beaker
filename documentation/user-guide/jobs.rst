Jobs
~~~~

The purpose of a Job is to provide an encapsulation of Tasks. It is to
provide a single point of submission of these Tasks, and a single point
of reviewing the output and results of these Tasks. The Tasks within a
Job may or may not be related to each other; although it would make
sense to define Jobs based on the relationship of the Tasks within it.
Once a Job has been submitted you can not alter its contents, or pause
it. You can however cancel it (see :ref:`job-results`), and
alter its Recipe Set's priorities (you can only lower the priority level
if you are not in the admin group). Adjusting this priority upwards will
change which Recipe Set is run sooner, and vice a versa.

Job workflow
^^^^^^^^^^^^

To create a simple Job workflow, see the bkr workflow-simple command in
`beaker client <../installation-guide.html#beaker-client>`__.

.. _job-searching:

Job searching
^^^^^^^^^^^^^

To search for a Job, navigate to "Scheduler>Jobs" at the top of the page. To 
look up the "Job ID", enter a number in the search box and press the "Lookup ID 
button". See :ref:`system-searching` for further details on searching.

.. admonition:: Quick Searches

   By pressing the "Running", "Queued", or "Completed" buttons you can quickly 
   display Recipes that have a status of running,queued, and completed 
   respectively. 

.. _job-submission:

Job submission
^^^^^^^^^^^^^^

There are two ways of submitting a Job through the web app.They are
outlined below.

.. _submitting-a-new-job:

Submitting a new job
''''''''''''''''''''

Once you have created an XML Job workflow, you are able to submit it as
a new "Job". To do this, go to the "Scheduler > New Job". Click "Browse"
to select your XML file, and then hit the "Submit Data" button. The next
page shown gives you an opportunity to check/edit your XML before
queuing it as a Job by pressing the "Queue" button.

.. _cloning:

Cloning an existing job
'''''''''''''''''''''''

Cloning a Job means to take a Job that has already been run on the System, and 
re-submit it. To do this you first need to be on the :ref:`Job search 
<job-searching>` page.

.. figure:: job_submit_clone.png
   :width: 100%
   :alt: [screenshot of job clone page]

   Cloning a Job

Clicking on "Clone" under the Action column will take you to a page that
shows the structure of the Job in the XML.

.. admonition:: Submitting a slightly different job

   If you want to submit a Job that's very similar to a Job already in
   Beaker,you can use the Clone button to change details of a previous Job
   and resubmit it!

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
    </ob>

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
        <recipeset>
        </recipeset>
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
        <recipeset>
          <recipe kernel_options="" kernel_options_post="" ks_meta="" role="None" whiteboard="Lab Controller">
          </recipe>
        </recipeset>
    </job>

.. admonition:: Avoid having many recipes in one recipe set

   Because recipes within a recipe set are required to run simultaneously,
   no recipe will commence execution until all other sibling recipes are
   ready. This involves each recipe reserving a system, and waiting until
   every other recipe has also reserved a system. This can tie up resources
   and keep them idle for long amounts of time. It is thus worth limiting
   the recipes in each recipeset to only those that actually need to run
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
how to utilize their templating language, see the `admin
guide <../admin-guide/kickstarts.html>`__.

.. _job-results:

Job results
'''''''''''

The whole purpose of Jobs is to view the output of the Job, and more to
the point, Tasks that ran within the Job. To do this, you must first go
to the :ref:`Job search <job-searching>` screen. After finding the Job you
want to see the results of, click on the link in the "ID" column.You
don't have to wait until the Job has completed to view the results. Of
course only the results of those Tasks that have already finished
running will be available.

The Job results page is divided by recipe set. To show the results of
each Recipe within these Recipe Sets, click the "Show All Results"
button. You can just show the tasks that have a status of "Fail" by
clicking "Show Failed Results."

While your Job is still queued it's possible to change the priority. You
can change the priority of individual Recipe Sets by changing the value
of "Priority", or you can change all the Job's Recipe Sets at once by
clicking an option beside the text "Set all RecipeSet priorities", which
is at the top right of the page. If successful, a green success message
will briefly display, otherwise a red error message will be shown.

.. admonition:: Priority permissions

   If you are not an Admin you will only be able to lower the priority.
   Admins can lower and raise the priority

.. figure:: job_priority_change.png
   :width: 100%
   :alt: [screenshot of changing priority]

   Changing the priority of a Job's Recipe Set

Result Details

-  *Run*

   -  This is the "ID" of the instance of the particular Task.

-  *Task*

   -  A Task which is part of our current Job.

-  *Start*

   -  The time at which the Task commenced.

-  *Finish*

   -  The time at which the Task completed.

-  *Duration*

   -  Time the Task took to run.

-  *Logs*

   -  This is a listing of all the output logs generated during the
      running of this Task.

-  *Status*

   -  This is the current Status of the Task. "Aborted","Cancelled" and
      "Completed" mean that the Task has finished running.

-  *Action*

   -  The two options here are Cancel and Clone. See :ref:`cloning` 
      to learn about cloning.

.. admonition:: Viewing Job results at a glance

   If you would to be able to look at the Result of all Tasks within 
   a particular Job, try the :ref:`Matrix Report <matrix-report>`.
