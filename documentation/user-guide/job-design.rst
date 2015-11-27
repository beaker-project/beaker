.. job-design.rst

Job design
==========

The goal of this section is to help you translate the material needs of your
particular use case into a suitably designed Beaker job. This means taking the
business, technical and management requirements and solving these within the various
levels of the job schema.

.. _job-access-control:

Access control for jobs
-----------------------

When submitting a job, you can optionally submit it on behalf of a group, or on
behalf of another user.

By default, only the submitter can modify job attributes (retention tag, 
product, whiteboard, priority, ack/nak), cancel the job, or delete the job.

However, when you submit a job on behalf of a group, members of that group have
full control over the job. All members of the group will also have SSH based 
access to the systems used by the job.
To learn how to set the group value, see :ref:`job-workflow-details`.

Submitting a job on behalf of another user means that, aside from allowing
the submitter to retain administrative access to the job, Beaker will treat
the job as being owned by the named user (the user named in the user
attribute) rather than the submitter. Since this gives the submitter access to
systems for scheduling purposes as if they were the named user, this is only
permitted if the submitter has been :ref:`configured as a submission
delegate<submission-delegates>` by that user. This is intended primarily to
grant automated tools the ability to submit and manage jobs on behalf of users,
without needing access to those users' credentials, and without granting them
the ability to perform other activities as that user (like managing systems or user groups).


.. _log-archiving-details:

Log archiving
-------------

Preserving log files indefinitely can consume an undesirable amount of
space. This behaviour can be controlled by selecting the appropriate
"retention tag" setting. Beaker ships with the following default retention
tags:

* ``scratch``: preserve logs for 30 days
* ``60days``: preserve logs for 60 days
* ``120days``: preserve logs for 120 days
* ``active``: preserve as long as associated product is active
* ``audit``: preserve indefinitely (no automatic deletion)

The log deletion utility provided with Beaker can automatically handle
deletion of logs for jobs using any of the first three retention tags.

The last two retention tags require that the job be associated with a
specific "Product". Product identifiers are treated as an opaque string
by Beaker - these two tags are intended for use in conjunction with external
tools and processes that are able to determine when a product is no longer
active or when an audit has been completed.
