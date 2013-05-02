.. job-design.rst

Job design
~~~~~~~~~~

The goal of this section is to help you translate the material needs of your
particular use case into a suitably designed Beaker job. This means taking the
business, technical and management requirements and solving these within the various
levels of the job schema.

Access control for jobs
^^^^^^^^^^^^^^^^^^^^^^^
When submitting a job, you can optionally submit it on behalf of a group.
This allows the possibility for group management of jobs.

By default the submitter is the only person who can modify the job (except for
any member of any group the submitter belongs to; they can ack/nack the job).
However, when you submit a job on behalf of a group, members of that group have
full control over the job.

Specifying a group will give members of that group the following access:-

- SSH based access to the system the job is running on.
- Full control over the job, equivalent to that of the owner.

To learn how to set the group value, see :ref:`job-workflow-details`.
