.. _reporting-queries:

Reporting from the Beaker database
==================================

Beaker's integration with Graphite can provide useful insights into the 
real-time health and performance of your Beaker installation (see 
:ref:`graphite`). However, for more in-depth analysis you may prefer to use an 
external query/reporting tool to extract data directly from Beaker's database.

Beaker's source includes a number of supported reporting queries which
may be useful for your Beaker site. They are installed with the
``beaker-server`` package under
``/usr/lib/python*/site-packages/bkr/server/reporting-queries``, or you
can `browse the queries online in Beaker's
git <https://github.com/beaker-project/beaker/tree/master/Server/bkr/server/reporting-queries>`_
(be sure to select the correct branch for your version of Beaker). These
queries are "supported" in the sense that they are tested by Beaker's
test suite, and if the queries require changes in future releases this will
be called out in the release notes. Advance warning will also be provided
for any such changes on the `beaker-devel mailing list`_.

.. _beaker-devel mailing list: https://lists.fedorahosted.org/archives/list/beaker-devel@lists.fedorahosted.org/

The supported SQL queries are written using the MySQL SQL dialect, and
automatically tested against MySQL. Accordingly, they may require translation
in order to be used with tools based on other SQL dialects.

These queries are intended to provide guidance for "interesting questions"
that a business intelligence system connected to Beaker may want to answer.
They can be tweaked to use different statistical functions, query different
date ranges, adapt filtering rules from another supported query,
parametrized in a reporting tool, etc.

As noted above, Beaker's database schema is subject to change in future
releases. If your external reporting queries stray beyond the schema
assumptions captured in the supported queries, then your queries may break
without notice when upgrading to a new Beaker release. If this occurs, you
must then examine the detailed schema upgrade notes for that release and
ensure the reporting tool's queries are updated as necessary. 

Suggestions for additional supported queries are welcome, and may be filed
as enhancement requests for the `Beaker community project`_ in GitHub.

.. _Beaker community project: https://github.com/beaker-project/beaker/issues/
