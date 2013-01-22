Beaker interface for administrators
===================================

Some functionality in Beaker’s web interface is restricted to administrators. 
Most of this functionality is accessed from the :guilabel:`Admin` menu.

Groups
------

Users can be grouped together in groups. A user can belong to one or
more groups. Similarly, a system can belong to one or more groups. If a
shared system belongs to a group, it can only be used by members of that
group.

*Adding a Group*.
To add a new group, select :menuselection:`Admin --> Groups` from the menu and 
then click the :guilabel:`Add ( + )` link at the bottom left. You'll then be 
prompted to enter a "Display Name" and a "Group Name". The former is the name 
that users of Beaker will see, and the latter is the name used internally. It's 
fine to have these names the same, or different.

*Editing a Group*.
To edit a group, select :menuselection:`Admin --> Groups` and click on the name 
of the group you wish to edit. From here you can add users, systems, and 
permissions to the group, as well as changing its display name and group name.

*Group Activity*.
To search through the historical activity of all groups, select 
:menuselection:`Activity --> Groups` from the menu.

External reports
----------------

If you are using external tools to produce reports about your Beaker site (for 
example, using Beaker's :ref:`Graphite integration <graphite>` or a business 
intelligence tool), you can link to the reports from the "External Reports" 
page in Beaker. Select :menuselection:`Reports --> External` from the menu.

This page displays a grid of links to external reports. When you are logged in 
as an administrator you can also modify the external report links from this 
page.

To add a new report, click :guilabel:`Add Report ( + )` at the bottom of the 
page and fill in the report's name, URL, and a short description to appear 
underneath it.

You can edit or delete a report by clicking the respective link below each 
report.

.. _admin-configuration:

Configuration
-------------

Some Beaker configuration is stored in the database rather than in the server 
configuration file, and can be changed without restarting Beaker services. 
Select :menuselection:`Admin --> Configuration` from the menu to view and 
change settings.
