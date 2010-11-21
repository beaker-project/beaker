XML-RPC methods
===============

These XML-RPC methods form part of the public API exposed by Beaker. The 
:command:`bkr` command-line client (distributed with Beaker) uses these methods 
to interact with the Beaker server. Users may also invoke them directly. The 
Python standard library includes an XML-RPC client library (:mod:`xmlrpclib`); 
the `Kobo`_ utility library may also be of interest.

The XML-RPC endpoint URL is ``/RPC2`` (relative to the base URL of the Beaker server).

Beaker uses XML-RPC internally for communication between the lab 
controller and the server. The internal API is not documented here.

.. _Kobo: https://fedorahosted.org/kobo/


Authentication
--------------

XML-RPC methods in the :mod:`auth` namespace allow the caller to begin or end an 
authenticated session with Beaker.

Beaker uses HTTP cookies to track sessions across XML-RPC calls. When calling 
the :meth:`auth.login_*` methods below, the response will include an HTTP 
cookie identifying the session. The caller must use this cookie in 
subsequent requests which belong with this session.

.. currentmodule:: bkr.server.authentication

.. automethod:: auth.login_krbV

.. automethod:: auth.login_password

.. automethod:: auth.logout


Distros
-------

The following XML-RPC methods allow the caller to fetch and manipulate distros 
recorded in Beaker.

.. currentmodule:: bkr.server.distro

.. automethod:: distros.filter

.. automethod:: distros.edit_version

.. automethod:: distros.tag

.. automethod:: distros.untag


Task library
------------

These XML-RPC methods fetch and manipulate tasks in the Beaker task library.

.. currentmodule:: bkr.server.tasks

.. automethod:: tasks.to_dict

.. automethod:: tasks.filter

.. automethod:: tasks.upload


DOCUMENTME
----------

.. currentmodule:: bkr.server.task_actions

.. automethod:: taskactions.stop

.. automethod:: taskactions.to_xml

.. automethod:: taskactions.task_info

.. currentmodule:: bkr.server.jobs

.. automethod:: jobs.upload

.. automethod:: jobs.delete_jobs

.. automethod:: jobs.list

..
   These ones can't use autodoc because their names confuse it :-(

.. currentmodule:: None

.. function:: recipes.tasks.extend

.. function:: recipes.tasks.watchdog

.. function:: lab_controllers
