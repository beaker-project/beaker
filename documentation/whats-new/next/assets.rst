Static web assets served from /assets
=====================================

Beaker uses a new URL prefix for static web assets, ``/assets``. To ensure 
assets are served correctly, add the following configuration to 
``/etc/httpd/conf.d/beaker-server.conf``. Adjust the ``/bkr`` prefix as 
appropriate for your installation.

::

    Alias /bkr/assets /usr/share/bkr/server/assets

    # Generated assets have a content hash in their filename so they can
    # safely be cached forever.
    <Directory /usr/share/bkr/server/assets/generated>
        ExpiresActive on
        ExpiresDefault "access plus 1 year"
    </Directory>
