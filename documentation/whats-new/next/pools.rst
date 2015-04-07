Shared access policies and System pools
=======================================

As part of the introduction of :ref:`shared-access-policies`, Beaker 20
introduces the concept of a :term:`system pool`.

Previously, a group in Beaker could contain both users and
systems. However, groups predominantly was a way for managing
Beaker users, rather than both. With the introduction of system pools,
existing groups will exclusively be "user groups" and thus states the
role of groups explicitly. It will no longer be possible to add
systems to user groups.

As part of the upgrade to Beaker 20, for each user group which contained one
or more systems, a new system pool will be created with the systems already
added to it. These pools will be created with the same name as the
user group, description set as "Pool migrated from group <group_name>"
and it's owning group set to the group.

A new Job XML element ``<pool/>`` has been added with the same
functionality as the existing ``<group/>`` element which is still
available, but considered deprecated.
