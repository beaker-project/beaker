New cache directory for web assets
==================================

In order to support customizable themes, the Beaker web application now builds 
web assets at runtime instead of during the package build process. As a result, 
generated assets are now located in a different directory 
(:file:`/var/cache/beaker/assets` rather than 
:file:`/usr/share/bkr/server/assets/generated`).

The Apache configuration in :file:`/etc/httpd/conf.d/beaker-server.conf` must 
be updated to reflect the new location for generated assets.

Add a new ``Alias`` directive *before* the existing ``Alias`` for 
``/bkr/assets``. Remember to remove or adjust the ``/bkr`` prefix as 
appropriate for your installation.

::

    Alias /bkr/assets/generated /var/cache/beaker/assets

Replace the existing ``<Directory /usr/share/bkr/server/assets/generated>`` 
section with the following::

    <Directory /var/cache/beaker/assets>
        <IfModule mod_authz_core.c>
            # Apache 2.4
            Require all granted
        </IfModule>
        <IfModule !mod_authz_core.c>
            # Apache 2.2
            Order deny,allow
            Allow from all
        </IfModule>
        # Generated assets have a content hash in their filename so they can
        # safely be cached forever.
        ExpiresActive on
        ExpiresDefault "access plus 1 year"
    </Directory>
