Implicit job sharing is disabled
================================

Beaker 0.13 introduced the :ref:`group jobs <group-jobs-0.13>` feature, which 
allows group members full access to modify, cancel, and delete jobs submitted 
for their group. This was designed to replace the previous "implicit" job 
sharing model where any group member could modify or delete jobs submitted by 
any other member of any group.

Up until this release, the implicit job sharing behaviour was deprecated but 
was still enabled by default unless the Beaker administrator disabled it in the 
configuration. Starting from this release, implicit job sharing is disabled by 
default.

If you were relying on the implicit job sharing permissions, ensure that you 
and your group members submit group jobs. See :ref:`job-access-control`.

Beaker administrators can temporarily re-enable the implicit job sharing 
permissions by setting::

    beaker.deprecated_job_group_permissions.on = True

in :file:`/etc/beaker/server.cfg`, but this is not recommended because the new 
"inverted groups" feature in this release makes it trivial for any user to 
create a group containing all Beaker users, which would give them access to 
modify and delete every Beaker job under the deprecated implicit sharing model.

The implicit job sharing permissions will be deleted entirely in a future 
release.
