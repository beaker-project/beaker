HTTP resources
==============

Beaker exposes machine-readable representations of certain HTTP resources, for 
programmatic access to Beaker's data.

All URLs are given relative to the base URL of the Beaker server.

System inventory information
----------------------------

.. object::
   /
   /available/
   /free/
   /mine/

   These four URLs provide a list of systems in Beaker.

   The first, ``/``, includes all systems which are visible to the currently 
   logged-in user. The second, ``/available/``, lists only systems which are 
   available for running jobs by the current user. ``/free/`` is limited to 
   those systems which are free to be used right now (that is, they are not 
   currently running another job, nor are they reserved). The last, ``/mine/``, 
   lists only systems which are owned by the current user.

   All four variations support the following query parameters:

   .. object:: tg_format

      Desired format for the list of systems. Must be *html*, *atom*, or 
      absent.

      When this parameter is absent or set to *html*, Beaker will return the 
      list of systems in an HTML table suitable for human consumption in 
      a browser.
      
      When set to *atom*, the response will be an `Atom`_ feed. Each system is 
      represented by an ``<entry/>`` element in the feed. Each entry will 
      contain a number of ``<link rel="alternate"/>`` elements which point to 
      representations of the system (see below).


   .. object:: list_tgp_limit

      Number of systems to return in the list.

      By default, only the first 20 systems are returned in the list. (The HTML 
      representation includes pagination links, but there is no such facility 
      in the Atom representation.) Setting this parameter to 0 will return all 
      systems in the list.

   .. object::
      systemsearch-{N}.table
      systemsearch-{N}.operation
      systemsearch-{N}.value

      A filter condition for the list of systems.

      All three parameters should be passed together, with *<N>* replaced by an 
      index to group them. For example, to limit the list to systems 
      which belong to the "devel" group, pass these three parameters::

        systemsearch-0.table=System%2FGroup&
        systemsearch-0.operation=is&
        systemsearch-0.value=devel

      Additional filters can be applied by repeating the three parameters 
      with a different index. For example, to also limit the list to systems 
      with more than four logical CPUs, append these three parameters::

        systemsearch-1.table=CPU%2FProcessors&
        systemsearch-1.operation=greater+than&
        systemsearch-1.value=4

      For a list of supported filter criteria, please refer to the search box 
      on the system listing page.

   .. versionadded:: 0.6

.. object:: /view/{FQDN}

   Provides detailed information about a system. *{FQDN}* is the system's 
   fully-qualified domain name.

   .. object:: tg_format

      Desired format for the system information. Must be *html*, *rdfxml*, 
      *turtle*, or absent.

      When this parameter is absent or set to *html*, Beaker will return the 
      system information in HTML suitable for human consumption in a browser.

      When set to *rdfxml* or *turtle*, an `RDF`_ description of the system is 
      returned (serialized as `RDF/XML`_ or `Turtle`_, respectively). For 
      a detailed description of the RDF schema used, refer to 
      :file:`Common/bkr/common/schema/beaker-inventory.ttl`.

   .. versionadded:: 0.6
    
.. _Atom: http://tools.ietf.org/html/rfc4287
.. _RDF: http://www.w3.org/RDF/
.. _RDF/XML: http://www.w3.org/TR/REC-rdf-syntax/
.. _Turtle: http://www.w3.org/TeamSubmission/turtle/
