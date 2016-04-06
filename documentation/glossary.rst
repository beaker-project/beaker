Glossary
========

.. glossary::

   access policy
       See :term:`system access policy`.

   active access policy
      The currently effective system access policy. See :term:`system
      access policy` and :ref:`system-access-policies`.

   ack
       Short for "acknowledgment". When reviewing Beaker job results, this 
       means that a result has been reviewed and is valid. See also 
       :term:`nak`.

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

   group
       A group of one or more Beaker users.

   group job
       A job associated with a :term:`group`. All group members are permitted 
       to cancel or modify the job. Refer to :ref:`job-access-control`.

   group owner
       The Beaker user who is responsible for a group. Group owners have 
       control over the group, including adding and removing members.

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

   job owner
       The Beaker user responsible for a job. By default this is the user who 
       submitted the job, unless it was submitted by a :term:`submission 
       delegate` on behalf of the job owner instead.

   lab controller
       Main conduit of communication between systems and the beaker server.
       Main responsibilities include provisioning of systems, monitoring of
       systems via the external watchdog, transfer of system logs,
       reporting of recipe task results, and importing distros.

   loan recipient
       The Beaker user to whom a system has been loaned. A loan grants 
       exclusive use of a system. Refer to :ref:`loaning-systems`.

   nak
       Short for "negative acknowledgment". When reviewing Beaker job results, 
       this means that a result has been reviewed but is waived. See also 
       :term:`ack`, :term:`waiver`.

   pool access policy
       The :term:`system access policy` which is defined for a :term:`system
       pool` so that systems in the pool can share a common access
       policy. This does not regulate access to the system pool
       itself.

   quiescent period
       The 'quiescent period' is the minimum amount of time (in seconds)
       between power operations.

   owner
       See :term:`system owner`, :term:`job owner`, or :term:`group owner`.

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

   submission delegate
       A Beaker user (often an automated service) which is permitted to submit 
       jobs on behalf of other users. Refer to :ref:`Submission delegates 
       <submission-delegates>`.

   system
       These make up Beaker's inventory, and are the systems on which
       recipes are run. They may not necesarily be a bare metal machine,
       but could be a guest on a hypervisor.

   system access policy
       A set of rules which grant permissions on the system to other users and 
       groups in Beaker. Refer to :ref:`system-access-policies`.

   system owner
       The Beaker user responsible for maintaining a system. The system owner 
       has complete control over their system. When someone reports a problem 
       or requests a loan for the system, Beaker emails the request to the 
       system owner (and the rest of the notify CC list) for their attention.

   system pool
       A collection of systems form a system pool. A system pool can
       be created by any Beaker user and the owner can changed to
       either another user or another :term:`group`. A system pool has
       an :term:`pool access policy` associated with it. Refer to
       :ref:`system-pools` and :ref:`shared-access-policies`.

   system user
       The Beaker user who currently holds a reservation on a system (they are 
       *using* it, hence the term).

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

   waiver
       An acknowledgment that a result is invalid and should be disregarded. 
       Results can be waived by setting the response on the recipe set to 
       :term:`nak`.

   workflow
       A workflow is used to describe job templates for running jobs of a
       particular nature.
