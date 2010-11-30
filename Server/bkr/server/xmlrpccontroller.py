import sys
import logging
import xmlrpclib
import cherrypy
import turbogears
from turbogears import controllers

log = logging.getLogger(__name__)

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
            log.exception('Error handling XML-RPC method')
            # Can't marshal the result
            response = xmlrpclib.dumps(fault)
        except:
            log.exception('Error handling XML-RPC method')
            # Some other error; send back some error info
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % (sys.exc_type, sys.exc_value))
                )

        cherrypy.response.headers["Content-Type"] = "text/xml"
        return response

    # Compat with kobo client
    client = RPC2
