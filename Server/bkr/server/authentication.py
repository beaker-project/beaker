from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from xmlrpclib import ProtocolError
from turbogears.identity import IdentityException

import cherrypy
import time
import re

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

__all__ = ['Auth']

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
        if identity.current.anonymous:
            return True
        return False

    @cherrypy.expose
    def login_password(self, username, password):
        """
        Authenticates the current session using the given username and password.
        """
        visit_key = turbogears.visit.current().key
        user = identity.current_provider.validate_identity(username, password, visit_key)
        if user is None:
            raise IdentityException("Invalid username or password")
        return identity.current.visit_key

    # TODO: proxy_user
    @cherrypy.expose
    def login_krbV(self, krb_request, proxy_user=None):
        """
        Authenticates the current session using Kerberos.
        
        :param krb_request: KRB_AP_REQ message containing client credentials, 
            as produced by :c:func:`krb5_mk_req`
        :type krb_request: base64-encoded string

        This method is also available under the alias :meth:`auth.login_krbv`, 
        for compatibility with `Kobo`_.
        """
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
        visit_key = turbogears.visit.current().key
        user = identity.current_provider.validate_identity(username, 
                                                    None, visit_key, True)
        if user is None:
            raise IdentityException()
        return identity.current.visit_key

    # Alias kerberos login
    login_krbv = login_krbV

    @cherrypy.expose
    def logout(self, *args):
        """
        Invalidates the current session.
        """
        identity.current.logout()
        return True

# this is just a hack for sphinx autodoc
auth = Auth
