.. _http_resources:

HTTP resources
==============

Beaker exposes machine-readable representations of certain HTTP resources, for
programmatic access to Beaker's data.

All URLs are given relative to the base URL of the Beaker server.

Note that all HTTP resources listed here support content negotiation (or will
in future). Your API client must send a suitable :mailheader:`Accept` header in
all requests. For example, clients expecting to receive JSON formatted
responses should include ``Accept: application/json`` in all requests.

.. _pageable-json-collections:

Pageable JSON collections
-------------------------

.. Note for Beaker devs: this describes the functionality provided by the
   @json_collection decorator in bkr.server.flask_util.

A number of Beaker server APIs return "pageable JSON collections", which share
some common characteristics described here.

The following query parameters are supported by pageable JSON collections:

``page_size=<int>``
    Return this many elements per page in the response.

    If this query parameter is not present, the response includes all elements
    in the collection. However, in cases where this would produce a very large
    response body, Beaker enforces pagination by redirecting the request to
    include a suitable page size. Therefore it is recommended that clients
    always include this parameter.

``page=<int>``
    Return this page number within the collection. Pages are numbered from 1.

``q=<query>``
    Apply this filter to the collection, prior to pagination. The query uses
    `Lucene query parser syntax`_:

    * ``field:value`` finds rows where ``field`` is equal to ``value``
    * ``value`` finds rows where any field is equal to ``value``
    * ``"`` quotes phrases, as in ``field:"value with space"``
    * ``-field:value`` finds rows where ``field`` is not equal to ``value``
    * ``field:[1 TO 10]`` finds rows where ``field`` is between 1 and 10
      inclusive

    Each API endpoint lists the supported query fields, but in general the
    field names correspond to the keys in the JSON objects for each element.

``sort_by=<field>``
    Sort elements by this field, prior to pagination. Each API endpoint lists
    the supported sort fields.

``order=asc|desc``
    Must be ``asc`` or ``desc``. Sorts in ascending or descending order,
    respectively.

The response is a JSON object with the following keys:

``q``
    Filter which was applied to the collection.

``count``
    Total number of elements in the (possibly filtered) collection.

``page_size``
    Number of elements in each page. This is the same as the ``page_size``
    query parameter if given, unless the requested page size was larger than
    allowed.

``page``
    Index of this page within the entire collection. The index of the first
    page is 1.

``sort_by``, ``order``
    If a custom sort order was requested with the ``sort_by`` and ``order``
    query parameters, their values are included in the response.

``entries``
    A JSON array containing all the elements of the collection making up this
    page in sorted order.

Authentication
--------------

Beaker uses HTTP cookies to track sessions across HTTP calls.
When calling the login_*() methods below, the response will include an HTTP
cookie identifying the session. The caller must use this cookie in subsequent
requests which belong with this session.

.. autoflask:: bkr.server.wsgi:app
   :endpoints: login_password, login_krbv, login_oauth2, logout, who_am_i

Systems
-------

.. http:get::
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

   .. object:: xmlsearch

      As an alternative to the ``systemsearch`` filter, you can pass XML
      filter criteria in this parameter. It supports the same criteria as in
      the ``<hostRequires/>`` element in Beaker job XML.

.. http:get:: /view/(fqdn)

   Provides detailed information about a system.

   :param fqdn: The system's fully-qualified domain name.
   :queryparam tg_format: Desired format for the system information. Must be
      *html*, *rdfxml*, *turtle*, or absent.

   When the *tg_format* parameter is absent or set to *html*, Beaker will
   return the system information in HTML suitable for human consumption in
   a browser. When set to *rdfxml* or *turtle*, an `RDF`_ description of the
   system is returned (serialized as `RDF/XML`_ or `Turtle`_, respectively).
   For a detailed description of the RDF schema used, refer to
   :file:`Common/bkr/common/schema/beaker-inventory.ttl`.

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_system, add_system, update_system, add_system_note,
     get_system_note, update_system_note, report_problem, get_system_activity,
     get_system_executed_tasks

.. _system-access-policies-api:

System access policy
--------------------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_system_access_policy, get_active_access_policy, save_system_access_policy, add_system_access_policy_rule,
     delete_system_access_policy_rules

System reservations
-------------------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: reserve, update_reservation

System loans
------------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: request_loan, grant_loan, update_loan

System provisioning
-------------------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: provision_system, get_system_command_queue, system_command

.. _Atom: http://tools.ietf.org/html/rfc4287
.. _RDF: http://www.w3.org/RDF/
.. _RDF/XML: http://www.w3.org/TR/REC-rdf-syntax/
.. _Turtle: http://www.w3.org/TeamSubmission/turtle/
.. _Lucene query parser syntax: http://lucene.apache.org/core/2_9_4/queryparsersyntax.html

System pools
------------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_pools, get_pool, create_pool, update_pool, delete_pool,
     add_system_to_pool, remove_system_from_pool, get_access_policy,
     save_access_policy, add_access_policy_rule, delete_access_policy_rules

Jobs
----

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_job, job_junit_xml, update_job, update_job_status,
     delete_job, get_job_activity, submit_inventory_job

Recipe sets
-----------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_recipeset, update_recipeset, update_recipeset_by_taskspec,
     update_recipeset_status

Recipes
-------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_recipe, update_recipe, get_recipe_log,
     update_reservation_request, extend_watchdog, extend_watchdog_by_taskspec,
     extend_watchdog_by_fqdn

Recipe tasks
------------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_recipe_task_log, get_recipe_task_result_log, get_recipe_task_comments,
     post_recipe_task_comment, get_recipe_task_result_comments, post_recipe_task_result_comment

Activity
--------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_activity, get_distro_activity, get_distro_tree_activity,
     get_group_activity, get_lab_controller_activity, get_systems_activity

Power types
-----------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_powertypes, delete_powertype, create_powertype


Groups
------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_groups, create_group, get_group, update_group, delete_group,
     add_group_membership, remove_group_membership,
     grant_ownership, revoke_ownership, add_permission, remove_permission,
     exclude_user, readd_user

Users
-----

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_users, create_user, get_user, get_self, update_user,
     add_ssh_public_key, delete_ssh_public_key, add_submission_delegate,
     delete_submission_delegate, create_keystone_trust,
     create_keystone_trust_for_self, delete_keystone_trust

Lab Controllers
---------------

.. autoflask:: bkr.server.wsgi:app
   :endpoints: get_labcontroller, update_labcontroller, create_labcontroller

Tasks
-----

.. autoflask:: bkr.server.wsgi:app
   :endpoints: update_task
