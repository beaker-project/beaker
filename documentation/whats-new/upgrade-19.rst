Upgrading to Beaker 19
======================

These instructions are for administrators upgrading a Beaker installation from 
0.18 to 19.

Database changes
----------------

The :program:`beaker-init` command now supports fully automatic database schema 
upgrades and downgrades. It can upgrade Beaker databases from version 0.11 or 
higher.

If you are upgrading from a Beaker version earlier than 0.11, you must first 
manually migrate the database up to version 0.11 by following the database 
upgrade instructions in the release notes for each prior version.
