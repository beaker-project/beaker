Automatic database migration
============================

The :program:`beaker-init` command now supports fully automatic database 
migrations using `Alembic <http://alembic.readthedocs.org/>`__. It can upgrade 
Beaker databases from version 0.11 or higher.

If you are upgrading from a Beaker version earlier than 0.11, you must first 
manually migrate the database up to version 0.11 by following the database 
upgrade instructions in the release notes for each prior version.
