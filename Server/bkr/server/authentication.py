from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, \
        error_handler, validators, redirect, paginate, identity
from turbogears.widgets import AutoCompleteField
from turbogears.identity import IdentityException
from turbogears.identity.saprovider import SqlAlchemyIdentity
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.model import *
from xmlrpclib import ProtocolError
import cherrypy
import time
import re
import logging
import string

log = logging.getLogger(__name__)

__all__ = ['Auth']

def proxy_identity(current_identity, proxy_user_name):
    if 'proxy_auth' not in current_identity.permissions:
        raise IdentityException('%s does not have proxy_auth permission' % user.user_name)
    proxy_user = User.by_user_name(proxy_user_name)
    if not proxy_user:
        log.warning('Attempted to proxy as nonexistent user %s', proxy_user_name)
        return None
    log.info("Associating proxy user (%s) with visit (%s)",
            proxy_user_name, current_identity.visit_key)
    # XXX shouldn't assume a particular implementation class here:
    return SqlAlchemyIdentity(current_identity.visit_key, proxy_user)

class Auth(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    KRB_AUTH_PRINCIPAL = get("identity.krb_auth_principal")
    KRB_AUTH_KEYTAB = get("identity.krb_auth_keytab")

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def who_am_i(self):
        """
        Returns the username of the currently logged in user.
        Provided for testing purposes.

        .. versionadded:: 0.6
        """
        return identity.current.user.user_name

    @cherrypy.expose
    def renew_session(self, *args, **kw):
        """
        Renew session, here to support kobo.
        """
        if identity.current.anonymous:
            return True
        return False

    @cherrypy.expose
    def login_password(self, username, password, proxy_user=None):
        """
        Authenticates the current session using the given username and password.

        The caller may act as a proxy on behalf of another user by passing the 
        *proxy_user* argument. This requires that the caller has 'proxy_auth' 
        permission.

        :param proxy_user: username on whose behalf the caller is proxying
        :type proxy_user: string or None
        """
        visit_key = turbogears.visit.current().key
        user = identity.current_provider.validate_identity(username, password, visit_key)
        if user is None:
            raise IdentityException("Invalid username or password")
        if proxy_user:
            proxied_user = proxy_identity(user, proxy_user)
            if proxied_user is None:
                raise IdentityException('Failed to authenticate on behalf of %s' % proxy_user)
        return identity.current.visit_key

    @cherrypy.expose
    def login_krbV(self, krb_request, proxy_user=None):
        """
        Authenticates the current session using Kerberos.

        The caller may act as a proxy on behalf of another user by passing the 
        *proxy_user* argument. This requires that the caller has 'proxy_auth' 
        permission.
        
        :param krb_request: KRB_AP_REQ message containing client credentials, 
            as produced by :c:func:`krb5_mk_req`
        :type krb_request: base64-encoded string
        :param proxy_user: username on whose behalf the caller is proxying
        :type proxy_user: string or None

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
        user = identity.current_provider.validate_identity(
                user_name=username, password=None,
                visit_key=visit_key, krb=True)
        if user is None:
            raise IdentityException()
        if proxy_user:
            proxied_identity = proxy_identity(user, proxy_user)
            if proxied_identity is None:
                raise IdentityException('Failed to authenticate on behalf of %s' % proxy_user)
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
