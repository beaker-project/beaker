import sys
import logging
import xmlrpclib
import jsonrpclib
from datetime import datetime
import cherrypy, cherrypy.config
import turbogears
from turbogears import controllers
from turbogears.identity.exceptions import IdentityFailure, IdentityException


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
        obj = Root
        # Get the function and make sure it's exposed.
        for name in method.split('.'):
            obj = getattr(obj, name, None)
            # Use the same error message to hide private method names
            if obj is None or not getattr(obj, "exposed", False):
                raise AssertionError("method %s does not exist in %s" % (name, obj))

        # Call the method, convert it into a 1-element tuple
        # as expected by dumps
        response = obj(*params)
        return response


    @turbogears.expose()
    def RPC2(self, *args, **kw):
        request_body = cherrypy.request.body.read()
        rpclib = GenericHTTPRPC()
        params, method, rpcid = rpclib.loads(request_body)
        start = datetime.utcnow()
        try:
            if method == "RPC2":
                # prevent recursion
                raise AssertionError("method cannot be 'RPC2'")
            response = self.process_rpc(method,params) # XXX This should probbaly be moved into GenericHTTPRPC
            response = rpclib.dumps((response,), methodresponse=True, allow_none=True, rpcid=rpcid)
        except (IdentityFailure, IdentityException), e:
            response = rpclib.dumps(rpclib.Fault(1,
                    '%s: Please log in first' % e.__class__))
        except (xmlrpclib.Fault, jsonrpclib.Fault), fault: # XXX not ideal
            log.exception('Error handling RPC method')
            # Can't marshal the result
            response = rpclib.dumps(fault)
        except:
            log.exception('Error handling RPC method')
            # Some other error; send back some error info
            response = rpclib.dumps(
                rpclib.Fault(1, "%s:%s" % (sys.exc_type, sys.exc_value))
                )
        log.debug('Time: %s %s %s', datetime.utcnow() - start, str(method), str(params)[0:50])
        rpclib.set_response_header()
        return response

    # Compat with kobo client
    client = RPC2


class GenericHTTPRPC:

    _json_type = 1;
    _xml_type = 2;

    def __init__(self, *args, **kw):
        content_type = cherrypy.request.headers.get('Content-Type').split('/')[1:].pop()
        if 'xml' in content_type:
            self.lib = xmlrpclib
            self._type = self._xml_type
        elif 'json' in content_type:
            self.lib = jsonrpclib
            self._type = self._json_type
        else:
            raise ValueError('Content type of %s is unrecognized' % content_type)

    def set_response_header(self):
        if self._type == self._json_type:
            cherrypy.response.headers["Content-Type"] = "application/json"
        else:
            cherrypy.response.headers["Content-Type"] = "text/xml"


    def loads(self, body):
        if self.lib is jsonrpclib:
            return self._json_loads(body)
        else:
            params, method = self.lib.loads(body)
            return (params, method, None)

    def dumps(self, response, *args, **kw):
        if self._type == self._xml_type:
            if 'rpcid' in kw: # this is a jsonrpc thing only
                del kw['rpcid']
        else:
            response = response[0]
        response = self.lib.dumps(response, *args, **kw)
	return response

    def __getattr__(self,name):
        return getattr(self.lib, name)

    def _xml_loads(self, body):
        return self.lib.loads(body)

    @classmethod
    def _json_loads(cls, body):
        data = jsonrpclib.loads(body)
        method = data['method']
        params = data.get('params', [])
        if params:
            if type(params[0]) is type([]): #it does not do list expansion for us
		        params = params[0]
		
        rpcid = data['id']
        return (params, method, rpcid)
