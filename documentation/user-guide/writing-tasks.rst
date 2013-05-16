Writing tasks
=============

Tasks are the building blocks of jobs in Beaker. Every recipe runs one or more 
tasks in sequence. The purpose of a task is to run commands on the system under 
test and report the results. For example, you could write a task to `configure 
an application for testing 
<http://git.beaker-project.org/cgit/beaker/tree/Tasks/distribution/beaker/setup/>`__ 
or `run its test suite 
<http://git.beaker-project.org/cgit/beaker/tree/Tasks/distribution/beaker/dogfood/>`__.

A Beaker task consists of at least three files: ``PURPOSE``, ``runtest.sh``, 
and a ``Makefile``. There can be other files as needed for the task. 
``PURPOSE`` is a text file that describes the task in some detail. There is no 
restriction on the length of the description. The core of each Beaker task is 
the ``runtest.sh`` script. It performs the testing (or delegates the work by 
invoking another script or executable) and reports the results. You may either 
write all the code that performs the test in the ``runtest.sh`` script or, when 
appropriate, call an external executable that does the bulk of the work. This 
external executable can be in any other language as long as it is appropriately 
executed from the ``runtest.sh`` script. Once you have written your test in 
this script, you can either run it locally (when appropriate) or package it as 
an RPM package and upload it to Beaker. The ``Makefile`` defines targets to 
carry out these and other related functions.

.. toctree::
   :maxdepth: 2

   example-task
   task-environment
   task-metadata
   multihost

.. todo::

   tortilla?
   LWD hooks
   KILLTIMEOVERRIDE
   other stuff used by rhts-test-runner etc
   other weird behaviour which rhts-test-runner does
   /etc/profile.d/task-defaults-rhts.sh
