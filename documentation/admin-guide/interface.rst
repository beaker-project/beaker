Beaker interface for administrators
===================================

Some functionality in Beaker’s web interface is restricted to
administrators. Most of this functionality is accessed from the "Admin"
menu.

Groups
------

Users can be grouped together in groups. A user can belong to one or
more groups. Similarly, a system can belong to one or more groups. If a
shared system belongs to a group, it can only be used by members of that
group.

*Adding a Group*.
To add a new group, go to "Admin -> Groups" and click the "Add ( + )"
link at the bottom left. You'll then be prompted to enter a "Display
Name" and a "Group Name". The former is the name that users of Beaker
will see, and the latter is the name used internally. It's fine to have
these names the same, or different.

*Editing a Group*.
To edit a group, go to "Admin -> Groups" and click on the name of the
group you wish to edit. From here you can add users, systems, and
permissions to the group, as well as changing its display name and group
name.

*Group Activity*.
To search through the historical activity of all groups, navigate to
"Activity -> Groups".

.. _admin-configuration:

Configuration
-------------

Some Beaker configuration is stored in the database rather than in the
server configuration file, and can be changed without restarting Beaker
services. Go to "Admin -> Configuration" to view and change settings.
