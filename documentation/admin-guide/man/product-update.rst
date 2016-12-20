.. _product-update:

product-update: Tool to update CPE identifiers for products in Beaker
=====================================================================

.. program:: product-update

Synopsis
--------

| :program:`product-update` [*options*]

Description
-----------

The :program:`product-update` command updates CPE identifiers for products in Beaker
from an XML file or URL.

Beaker administrators can setup a cron job on the beaker server to run this command
at regular intervals (e.g. daily).

Options
-------

.. option:: -c <path>, --config-file <path>

   Read server configuration from <path> instead of the default /etc/beaker/server.cfg.

.. option:: -p <file>, --product-file <file>

   Load product XML data from <file>

.. option:: --product-url <url>

   Load product XML or JSON data from <url>

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Update CPE identifiers for products in Beaker from a URL::

    product-update --product-url 'https://example.com/api/v1/releases/?fields=id,cpe'
