Glossary
========

.. glossary::

   Beaker server
       Comprised of two main parts, the web UI and the scheduler. The web
       UI is the main interface for Beaker users. The scheduler is
       responsible for processing job workflows and assigning to recipes,
       eventually culminating in the provisioning of systems via the lab
       controller.

   distro
       In Beaker, a distro represents an OS major + minor version. Unlike a
       distro tree, it says nothing about the arch or variant e.g.
       RHEL-6.2.

   distro tree
       A distro tree is what is installed onto a system. It is a
       combination of distro, variant and arch e.g. RHEL-6.2 Server
       x86\_64.

   FQDN
       Fully qualified domain name.

   guest recipe

       Guest recipes are used to run one or more recipe tasks in one
       or more virtual machines as part of a larger :term:`host
       recipe`.

   host recipe

       A host recipe is a :term:`recipe` which runs one or more guest
       recipes in virtual machines.

   job
       The highest unit of work in Beaker, it is a container for one or
       more recipe sets that are run independently of each other.

   lab controller
       Main conduit of communication between systems and the beaker server.
       Main responsibilities include provisioning of systems, monitoring of
       systems via the external watchdog, transfer of system logs,
       reporting of recipe task results, and importing distros.

   quiescent period
       The 'quiescent period' is the minimum amount of time (in seconds)
       between power operations.

   recipe set
       A recipe set is contained within a job and can contain one or more
       recipes. Any recipes within the same recipe set are run in parallel
       with each other. This is needed for multihost recipes.

   recipe
       A recipe is contained within a recipe set. A recipe is a unit of
       work, comprising an ordered sequence of recipe tasks that are run on
       a system.

   recipe task
       A recipe task is contained within a recipe and is the smallest unit
       of work in Beaker. A recipe task runs a specific task, the results
       of which are reported to the beaker server.

   system
       These make up Beaker's inventory, and are the systems on which
       recipes are run. They may not necesarily be a bare metal machine,
       but could be a guest on a hypervisor.

   task
       A task is designed to be run on a system, for the purposes of
       running some arbitrary code written by the task's author. A task is
       uploaded to Beaker as an RPM and is run as a recipe task (that is to
       say, a recipe task is an instance of a task).

   test harness
       The test harness is the software that manages the running of recipe
       tasks on the system. It installs the tasks, creates the environment
       in which they need to run, executes them in order, reports the
       results backs to the server and uploads the logs to the lab
       controller.

   workflow
       A workflow is used to describe job templates for running jobs of a
       particular nature.
