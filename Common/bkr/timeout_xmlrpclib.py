
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software # Foundation, either version 2 of the License, or
# (at your option) any later version.

import xmlrpclib
import httplib

def ServerProxy(url, *args, **kwargs):
   t = TimeoutTransport()
   t.timeout = kwargs.get('timeout', 40)
   if 'timeout' in kwargs:
       del kwargs['timeout']
   kwargs['transport'] = t
   serverproxy = xmlrpclib.ServerProxy(url, *args, **kwargs)
   return serverproxy

Server = ServerProxy

class TimeoutTransport(xmlrpclib.Transport):

   def make_connection(self, host):
       conn = TimeoutHTTP(host)
       conn.set_timeout(self.timeout)
       return conn

class TimeoutHTTPConnection(httplib.HTTPConnection):

   def connect(self):
       httplib.HTTPConnection.connect(self)
       # check whether socket timeout support is available (Python >= 2.3)
       try:
           self.sock.settimeout(self.timeout)
       except AttributeError:
           pass

class TimeoutHTTP(httplib.HTTP):
   _connection_class = TimeoutHTTPConnection

   def set_timeout(self, timeout):
       self._conn.timeout = timeout
