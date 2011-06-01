import sys
import logging
import xmlrpclib
from datetime import datetime
import cherrypy, cherrypy.config
import turbogears
from turbogears import controllers
from turbogears.identity.exceptions import IdentityFailure

log = logging.getLogger(__name__)

class RPCRoot(controllers.Controller):

    # We disable external /login redirects for XML-RPC locations,
    # because they make it impossible for us to grab IdentityFailure exceptions 
    # and report them nicely to the caller
    cherrypy.config.update({
        '/RPC2': {'identity.force_external_redirect': False},
        '/client': {'identity.force_external_redirect': False},
    })

    @turbogears.expose()
    def RPC2(self):
        params, method = xmlrpclib.loads(cherrypy.request.body.read())
        start = datetime.utcnow()
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
        except IdentityFailure, e:
            response = xmlrpclib.dumps(xmlrpclib.Fault(1,
                    '%s: Please log in first' % e.__class__))
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

        log.debug('Time: %s %s %s', datetime.utcnow() - start, str(method), str(params)[0:50])
        cherrypy.response.headers["Content-Type"] = "text/xml"
        return response

    # Compat with kobo client
    client = RPC2
