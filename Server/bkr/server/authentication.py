from turbogears.config import get
from bkr.common.bexceptions import BX
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.model import User
import cherrypy
import logging
import socket

log = logging.getLogger(__name__)

__all__ = ['Auth']

class LoginException(BX): pass

class Auth(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    KRB_AUTH_PRINCIPAL = get("identity.krb_auth_principal")
    KRB_AUTH_KEYTAB = get("identity.krb_auth_keytab")

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def who_am_i(self):
        """
        Returns an XML-RPC structure (dict) with information about the 
        currently logged in user.
        Provided for testing purposes.

        .. versionadded:: 0.6.0
        .. versionchanged:: 0.6.1
           Formerly returned only the username.
        .. versionchanged:: 1.0
           Also return the email address of user.
        """
        retval = {'username': identity.current.user.user_name,
                  'email_address' : identity.current.user.email_address}
        if identity.current.proxied_by_user is not None:
            retval['proxied_by_username'] = identity.current.proxied_by_user.user_name
        return retval

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
        user = User.by_user_name(username)
        if user is None:
            raise LoginException(_(u'Invalid username or password'))
        if not user.can_log_in():
            raise LoginException(_(u'Invalid username or password'))
        if not user.check_password(password):
            raise LoginException(_(u'Invalid username or password'))
        if proxy_user:
            if not user.has_permission(u'proxy_auth'):
                raise LoginException(_(u'%s does not have proxy_auth permission') % user.user_name)
            proxied_user = User.by_user_name(proxy_user)
            if proxied_user is None:
                raise LoginException(_(u'Proxy user %s does not exist') % proxy_user)
            identity.set_authentication(proxied_user, proxied_by=user)
        else:
            identity.set_authentication(user)
        return user.user_name

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
        user = User.by_user_name(username)
        if user is None:
            raise LoginException(_(u'Invalid username'))
        if not user.can_log_in():
            raise LoginException(_(u'Invalid username'))
        if proxy_user:
            if not user.has_permission(u'proxy_auth'):
                raise LoginException(_(u'%s does not have proxy_auth permission') % user.user_name)
            proxied_user = User.by_user_name(proxy_user)
            if proxied_user is None:
                raise LoginException(_(u'Proxy user %s does not exist') % proxy_user)
            identity.set_authentication(proxied_user, proxied_by=user)
        else:
            identity.set_authentication(user)
        return username

    # Alias kerberos login
    login_krbv = login_krbV

    @cherrypy.expose
    def logout(self, *args):
        """
        Invalidates the current session.
        """
        identity.clear_authentication()
        return True

# this is just a hack for sphinx autodoc
auth = Auth
