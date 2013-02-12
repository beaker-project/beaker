Redirect server API docs
========================

Server API docs are no longer included in the beaker-server package and served 
from apidocs/. They can be browsed on the Beaker web site instead.

Replace the following Alias directive in /etc/httpd/conf.d/beaker-server.conf::

    Alias /bkr/apidoc /usr/share/bkr/server/apidoc/html

with a Redirect directive (adjust the /bkr path prefix as appropriate for your 
site)::

    Redirect permanent /bkr/apidoc http://beaker-project.org/docs/server-api
