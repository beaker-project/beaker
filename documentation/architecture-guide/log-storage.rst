Log storage
===========

Log files are generated text files that contain the results and output
of things like recipe task results, recipe tasks, anaconda, serial console etc.

By default, log files will be stored on, served from, and potentially deleted from
the relevant lab controller of each recipe.

.. _architecture-archive-server:

Archive Server
--------------

You can configure the lab controller to work with an
:ref:`archive server <archive-server>`.
Beaker requires the archive server to be running a HTTP server and
`rsyncd <http://linux.die.net/man/5/rsyncd.conf>`_.
If you wish to be able to delete log files via :ref:`beaker-log-delete <beaker-log-delete>`,
you must `configure <http://httpd.apache.org/docs/2.2/mod/mod_dav.html>`_
the HTTP server to handle WebDAV DELETE operations on the log directory's
base path (HTTP digest and kerberos authentication are supported by
`beaker-log-delete`).

Once configured, the `beaker-transfer` daemon is used to rsync the log files
from the lab controller to the archive server. This means that there is
a window when the log files do still reside on the lab controller and are
available for viewing and deleting as they would be on the archive server.
Ensure that the HTTP server on the lab controller is configured to allow the
same level of access to the log files as is afforded the archive server.

The Apache configuration included with Beaker for serving logs from the lab 
controller includes this section, to ensure that log files are not 
misinterpreted as binary files. Apply the same configuration to the archive 
server::

    <Files "*.log">
        ForceType text/plain
    </Files>
