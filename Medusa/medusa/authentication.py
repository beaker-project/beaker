from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from medusa.xmlrpccontroller import RPCRoot
from medusa.helpers import *
from xmlrpclib import ProtocolError
from turbogears.identity import IdentityException

import cherrypy
import time
import re

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

class Auth(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    KRB_AUTH_PRINCIPAL = get("identity.krb_auth_principal")
    KRB_AUTH_KEYTAB = get("identity.krb_auth_keytab")

    @cherrypy.expose
    def renew_session(self, *args, **kw):
        """
        Renew session, here to support kobo.
        """
        return True

    @cherrypy.expose
    def login_password(self, *args, **kw):
        """
        Login via password
        """
        visit_key = turbogears.visit.current().key
        user = identity.current_provider.validate_identity(args[1], args[2], visit_key)
        if user is None:
            raise IdentityException("Invalid username or password")
        return identity.current.visit_key

    # TODO: proxy_user
    @cherrypy.expose
    def login_krbV(self, request, krb_request, proxy_user=None):
        """login_krbV(krb_request, proxy_user=None): session_key"""
        import krbV
        import base64

        context = krbV.default_context()
        server_principal = krbV.Principal(name=self.KRB_AUTH_PRINCIPAL, context=context)
        server_keytab = krbV.Keytab(name=self.KRB_AUTH_KEYTAB, context=context)
    
        auth_context = krbV.AuthContext(context=context)
        auth_context.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
        auth_context.addrs = (socket.gethostbyname(cherrypy.request.remote_host), 0, cherrypy.request.remote_addr, 0)
    
        # decode and read the authentication request
        decoded_request = base64.decodestring(krb_request)
        auth_context, opts, server_principal, cache_credentials = context.rd_req(decoded_request, server=server_principal, keytab=server_keytab, auth_context=auth_context, options=krbV.AP_OPTS_MUTUAL_REQUIRED)
        cprinc = cache_credentials[2]
    
        # remove @REALM
        username = cprinc.name.split("@")[0]
        print "username=", username
        visit_key = turbogears.visit.current().key
        user = identity.current_provider.validate_identity(username, 
                                                    None, visit_key, True)
        if user is None:
            raise IdentityException()
        return identity.current.visit_key

    @cherrypy.expose
    def logout(self, *args, **kw):
        """
        Logout session
        """
        identity.current.logout()
        return True

