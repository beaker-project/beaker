import sys
import logging
import xmlrpclib
from datetime import datetime
import cherrypy, cherrypy.config
import turbogears
from turbogears import controllers
from turbogears.database import session
from turbogears.identity.exceptions import IdentityFailure, get_identity_errors

log = logging.getLogger(__name__)

class RPCRoot(controllers.Controller):

    # We disable external /login redirects for XML-RPC locations,
    # because they make it impossible for us to grab IdentityFailure exceptions 
    # and report them nicely to the caller
    cherrypy.config.update({
        '/RPC2': {'identity.force_external_redirect': False},
        '/client': {'identity.force_external_redirect': False},
    })

    def process_rpc(self,method,params):
        """
        _process_rpc() handles a generic way of dissecting and calling
        methods and params with params being a list and methods being a '.'
        delimited string indicating the method to call

        """
        from bkr.server.controllers import Root
        #Is there a better way to do this?
        #I could perhaps use cherrypy.root, but this only works on prod
        obj = Root()
        # Get the function and make sure it's exposed.
        for name in method.split('.'):
            obj = getattr(obj, name, None)
            # Use the same error message to hide private method names
            if obj is None or not getattr(obj, "exposed", False):
                raise AssertionError("method %s does not exist" % name)

        # Call the method, convert it into a 1-element tuple
        # as expected by dumps
        response = obj(*params)
        return response

    @turbogears.expose()
    def RPC2(self, *args, **kw):
        params, method = xmlrpclib.loads(cherrypy.request.body.read(), use_datetime=True)
        start = datetime.utcnow()
        try:
            if method == "RPC2":
                # prevent recursion
                raise AssertionError("method cannot be 'RPC2'")
            response = self.process_rpc(method,params)
            response = xmlrpclib.dumps((response,), methodresponse=1, allow_none=True)
        except IdentityFailure, e:
            session.rollback()
            # IdentityFailure constructor fiddles with the response code,
            # so let's set it back
            cherrypy.response.status = 200
            identity_errors = get_identity_errors()
            response = xmlrpclib.dumps(xmlrpclib.Fault(1,"%s: %s" % (e.__class__,','.join(identity_errors))))
        except xmlrpclib.Fault, fault:
            session.rollback()
            log.exception('Error handling XML-RPC method')
            # Can't marshal the result
            response = xmlrpclib.dumps(fault)
        except:
            session.rollback()
            log.exception('Error handling XML-RPC method')
            # Some other error; send back some error info
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % sys.exc_info()[:2])
                )

        log.debug('Time: %s %s %s', datetime.utcnow() - start, str(method), str(params)[0:50])
        cherrypy.response.headers["Content-Type"] = "text/xml"
        return response

    # Compat with kobo client
    client = RPC2
