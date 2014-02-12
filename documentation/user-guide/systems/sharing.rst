Sharing your system with others
===============================

By default, when a new system is added to Beaker only the owner has access to 
use it. There are a number of mechanisms which you can use to share your system 
with other Beaker users.

.. _loaning-systems:

Loans
-----

Loaning a system to another user gives them exclusive access to reserve the 
system. While the system is loaned, no other users are permitted to reserve the 
system, even if they would normally have access to reserve it.

When loaning a system, you can optionally add a comment to record the reason 
for the loan. When the loan is returned, the comment is automatically cleared.

To loan your system, go to the system page and click the :guilabel:`Loan 
Settings` button in the :guilabel:`Loaned to` field.

.. _system-access-policies:

Access policies
---------------

You can apply an access policy to your system, in order to grant other Beaker 
users limited access to use it.

Access policies are represented as a set of rules. Each rule grants 
a particular permission to a particular user or group. The effective 
permissions for a user is the union of the permissions granted to them directly 
and to all of the groups they are a member of.

To apply an access policy to your system, go to the system page and click the 
:guilabel:`Access Policy` tab, or use the :ref:`bkr policy-grant 
<bkr-policy-grant>` client command.

In Beaker's web UI access policies are displayed as a table of checkboxes, 
where each column is a permission and each row is a user or group covered by 
the policy. When a checkbox is selected it represents a rule granting the 
permission in the column to the user or group in the row.

The following permissions can be granted in an access policy:

============== =================== ===========================================
Name           Label               Description
============== =================== ===========================================
edit_policy    Edit this policy    The user can edit the access policy to grant
                                   or revoke permissions, including adding new 
                                   users and groups to the policy. Users with
                                   permission to edit the policy can grant
                                   themselves any of the other permissions
                                   and also change the owner of the system.
edit_system    Edit system details The user can edit system details and
                                   configuration, however they cannot take 
                                   ownership of it or grant new permissions to 
                                   themselves or any other user.
loan_any       Loan to anyone      The user can lend the system to any Beaker
                                   user, including themselves. Users with this
                                   permission can also return and update any
                                   existing loan, as well as return other
                                   user's manual reservations.
loan_self      Loan to self        The user can borrow the system by loaning
                                   it to themselves.
control_system Control power       The user can run power commands and netboot
                                   commands for the system *even when they have 
                                   not reserved it*.
reserve        Reserve             The user can reserve the system, either
                                   through the scheduler (if the system is 
                                   Automated) or manually through the web UI 
                                   (if the system is Manual).
============== =================== ===========================================

In Beaker's web UI, the human-friendly label is used to identify permissions.
In the command-line client, the symbolic name is used.

The owner of the system is implicitly granted all of the above permissions,
and also has the ability to change the system owner.

Administrators of the Beaker instance are implicitly granted all of the same
permissions as the system owner except the ability to reserve the system (this
ensures admins don't accidentally run automated jobs on arbitrary systems).
If an administrator needs to reserve a system and do not already have access
to do so, they must first loan it to themselves or grant themselves the
relevant permission.

System reservations made through the automated scheduler can only be
terminated by cancelling the relevant job rather than by returning the system
directly through the web UI or command-line client.
