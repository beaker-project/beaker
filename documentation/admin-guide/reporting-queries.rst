Reporting from the Beaker database
==================================

Beaker's `integration with Graphite <#integration-with-graphite>`_ can
provide useful insights into the real-time health and performance of
your Beaker installation. However, for reporting on historical trends
you may prefer to use an external query/reporting tool to extract data
directly from Beaker's database.

Beaker's source includes a number of supported reporting queries which
may be useful for your Beaker site. They are installed with the
``beaker-server`` package under
``/usr/lib/python*/site-packages/bkr/server/reporting-queries``, or you
can `browse the queries online in Beaker's
git <http://git.beaker-project.org/cgit/beaker/tree/Server/bkr/server/reporting-queries>`_
(be sure to select the correct branch for your version of Beaker). These
queries are "supported" in the sense that they are tested by Beaker's
test suite, and if the queries are changed in future releases this will
be called out in the release notes.

Beware that Beaker's database schema is subject to change in future
releases, so if your external reporting tool uses any queries other than
the supported ones described above then you must examine the schema
upgrade instructions for every release and ensure the reporting tool's
queries are updated as necessary.
