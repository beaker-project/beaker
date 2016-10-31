What's New in Beaker 0.11?
==========================

Backwards-incompatible changes
------------------------------

In previous versions of Beaker, shell metacharacters in custom repo URLs were 
not escaped when writing to ``/etc/yum.repos.d``. In particular, if your custom 
repo URL contained a yum variable, it had to be escaped as ``\$`` to prevent 
bash from interpreting it. This escaping is no longer necessary. See bug 
:issue:`880039` for full details.

New reporting and metrics features
----------------------------------

Beaker now includes a number of "supported" reporting queries, which can be 
used for in-depth historical analysis of your Beaker installation. See 
:ref:`reporting-queries` for full details. (Contributed by Dan Callaghan and 
Raymond Mancy in :issue:`193142`, :issue:`591656`, :issue:`741960`, 
:issue:`877264`, :issue:`877272`, :issue:`877274`.)

Beaker's integration with the Graphite real-time metrics tool, originally added 
in version 0.9.4, has also been expanded. See :ref:`graphite` for details about 
the metrics Beaker sends to Graphite. (Contributed by Dan Callaghan and Nick 
Coghlan in :issue:`584783`, :issue:`695986`, :issue:`839583`).

If you are using an external reporting tool with your Beaker installation, you 
can add links to the reports on the new External Reports page. (Contributed by 
Raymond Mancy in :issue:`883606`.)

Documentation improvements
--------------------------

- Beaker's documentation is now in reStructuredText format and is built using 
  `Sphinx <http://sphinx-doc.org/>`_. It was also re-arranged to improve 
  clarity.
- The :doc:`Creating a task <../user-guide/example-task>` section has been improved and updated to describe 
  using :ref:`beaker-wizard <beaker-wizard>`. (Contributed by Amit Saha in 
  :issue:`872428`.)
- New sections were added to the Administration Guide describing :ref:`Graphite
  integration <graphite>` and :ref:`reporting queries <reporting-queries>`. 
  (Contributed by Dan Callaghan and Nick Coghlan.)
- The Installation Guide was removed in favour of targeted instructions in the 
  User and Administration Guides. (Contributed by Dan Callaghan.)

Other enhancements
------------------

- Default install options can be applied to an entire distro family. 
  (Contributed by Dan Callaghan in :issue:`873714`.)
- New kickstart snippet, ``timezone``, allowing administrators to customize the 
  default timezone per lab. (Contributed by Bill Peck in :issue:`876582`.)
- Users can change their own Beaker account password, if their account is using 
  password authentication. (Contributed by Raymond Mancy in :issue:`865676`.)
- The :ref:`bkr machine-test <bkr-machine-test>` command will avoid scheduling 
  recipes with distro families which are excluded for that system. (Contributed 
  by Bill Peck in :issue:`876752`.)
- New kickstart metadata variable, ``fstype``, to control filesystem type used 
  during installation. The distro default is used if no explicit filesystem 
  type is requested. (Contributed by Jun'ichi NOMURA in :issue:`865679`.)
- New kickstart metadata variable, ``linkdelay``, to add ``LINKDELAY`` to 
  network interface configuration files. (Contributed by Jun'ichi NOMURA in 
  :issue:`865680`.)
- Lab controller daemons use python-daemon for daemonizing. (Contributed by 
  James de Vries in :issue:`813574`.)
- Transaction handling and exception handling in beakerd is cleaner and 
  simpler. (Contributed by Dan Callaghan in :issue:`880853`.)

Bug fixes
---------

The following bugs were fixed in Beaker 0.11.0:

- :issue:`843854`: Clearing netboot config during post-install needs to be synchronous
- :issue:`869455`: Submitting a job with ``<package/>`` results in database error: (OperationalError) (1048, "Column 'job_id' cannot be null")
- :issue:`869758`: Custom repos using yum variables (such as ``$basearch``) cause installation to fail
- :issue:`872001`: Orphaned rendered_kickstart rows are not deleted
- :issue:`875535`: CPU flag filtering in hostRequires does not work
- :issue:`880039`: Shell metacharacters in repo URLs are not escaped correctly when written to ``/etc/yum.repos.d``
- :issue:`880424`: Identity extension fails to start during beaker-server RPM upgrade
- :issue:`880899`: ``op`` attribute is declared as mandatory in beaker-job.rng for many elements where it is not actually mandatory
- :issue:`881563`: Missing schema upgrade note to make recipe.recipe_set_id and recipe_set.job_id not NULLable
- :issue:`883214`: CPU speed filtering in hostRequires does not work when given a float value
- :issue:`883668`: Watchdog starts monitoring console too early in multi-host recipe sets
- :issue:`885554`: beakerd aborts recipes which have no systems, even if they could be satisfied by oVirt/RHEV
- :issue:`888673`: System can be returned from the system page while a recipe is running on it

The following bug was fixed in Beaker 0.11.1:

- :issue:`896622`: Submitting a job with ``<packages/>`` results in database error: (OperationalError) (1048, "Column 'recipe_id' cannot be null")

The following bug was fixed in Beaker 0.11.2:

- :issue:`903893`: Guest MAC address conflicts when guest recipe finishes before host recipe

The following bugs were fixed in Beaker 0.11.3:

- :issue:`902659`: oVirt incompatible recipes are incorrectly reported in the Graphite metrics as "dynamic_virt_possible"
- :issue:`903442`: Temporary workaround for :issue:`807237` (recipe Running when all tasks are Completed)
- :issue:`907297`: bkr.common.krb_auth.get_encoded_request() incorrectly guesses host portion of service principal
- :issue:`907307`: Dynamic virt should be precluded for non i386/x86_64 arches

Compatibility issues with Jinja 2.6 and SQLAlchemy 0.7 were also fixed in Beakeer 0.11.0.
