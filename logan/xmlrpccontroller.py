# Logan - Logan is the scheduling piece of the Beaker project
#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import xmlrpclib
import cherrypy
import turbogears
from turbogears import controllers

class RPCRoot(controllers.Controller):

    @turbogears.expose()
    def RPC2(self):
        params, method = xmlrpclib.loads(cherrypy.request.body.read())
        try:
            if method == "RPC2":
                # prevent recursion
                raise AssertionError("method cannot be 'RPC2'")
            # Get the function and make sure it's exposed.
            obj = self
            for name in method.split('.'):
            	obj = getattr(obj, name, None)
            	# Use the same error message to hide private method names
            	if obj is None or not getattr(obj, "exposed", False):
                	raise AssertionError("method %s does not exist" % name)

            # Call the method, convert it into a 1-element tuple
            # as expected by dumps                       
            response = obj(*params)
            response = xmlrpclib.dumps((response,), methodresponse=1, allow_none=True)
        except xmlrpclib.Fault, fault:
            # Can't marshal the result
            response = xmlrpclib.dumps(fault)
        except:
            # Added by dmalcolm: dump the traceback server-side for ease 
            # of debugging:
            if True:
                import traceback
                (type, value, tb) = sys.exc_info()
                try:
                    print "Exception type: %s"%type
                    print "Exception value: %s"%value
                except: pass # survive failure in stringification of value                   
                print "Traceback:"
                for line in traceback.format_tb(tb):
                    print line,

            # Some other error; send back some error info
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % (sys.exc_type, sys.exc_value))
                )

        cherrypy.response.headers["Content-Type"] = "text/xml"
        return response
