beaker-proxy uses gevent instead of SimpleXMLRPCServer
======================================================

This means beaker-proxy can efficiently handle many concurrent connections 
using a single process. Previously, a new handler process was forked for every 
request.
