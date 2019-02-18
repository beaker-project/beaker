
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import logging
import xmlrpclib
from datetime import datetime
import cherrypy, cherrypy.config
import turbogears
from turbogears import controllers
from turbogears.database import session
from bkr.server import identity
from formencode.api import Invalid

log = logging.getLogger(__name__)

class XMLRPCMethodDoesNotExist(TypeError): pass

class RPCRoot(controllers.Controller):

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
                raise XMLRPCMethodDoesNotExist(method)

        # Call the method, convert it into a 1-element tuple
        # as expected by dumps
        response = obj(*params)
        return response

    @turbogears.expose()
    def RPC2(self, *args, **kw):
        params, method = xmlrpclib.loads(cherrypy.request.body.read(), use_datetime=True) # pylint:disable=no-member
        if str(method).startswith('auth.'):
            log.debug('Handling %s', str(method))
        else:
            log.debug('Handling %s %s', str(method), str(params)[0:50])
        start = datetime.utcnow()
        try:
            if method == "RPC2":
                # prevent recursion
                raise AssertionError("method cannot be 'RPC2'")
            response = self.process_rpc(method,params)
            response = xmlrpclib.dumps((response,), methodresponse=1, allow_none=True)
            session.flush()
        except identity.IdentityFailure, e:
            session.rollback()
            response = xmlrpclib.dumps(xmlrpclib.Fault(1,"%s: %s" % (e.__class__, str(e))))
        except xmlrpclib.Fault, fault:
            session.rollback()
            log.exception('Error handling XML-RPC method')
            # Can't marshal the result
            response = xmlrpclib.dumps(fault)
        except XMLRPCMethodDoesNotExist as e:
            session.rollback()
            response = xmlrpclib.dumps(xmlrpclib.Fault(1,
                    'XML-RPC method %s not implemented by this server' % e.args[0]))
        except Invalid, e:
             session.rollback()
             response = xmlrpclib.dumps(xmlrpclib.Fault(1, str(e)))
        except Exception:
            session.rollback()
            log.exception('Error handling XML-RPC method')
            # Some other error; send back some error info
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % sys.exc_info()[:2])
                )

        if str(method).startswith('auth.'):
            log.debug('Time: %s %s', datetime.utcnow() - start, str(method))
        else:
            log.debug('Time: %s %s %s', datetime.utcnow() - start, str(method), str(params)[0:50])
        cherrypy.response.headers["Content-Type"] = "text/xml"
        return response

    # Compat with the migrated kobo client
    client = RPC2
