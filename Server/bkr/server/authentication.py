# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import socket

import requests
from flask import request
from flask import jsonify

from bkr.common.bexceptions import BX
from bkr.server import identity
from bkr.server.app import app
from bkr.server.flask_util import auth_required, read_json_request
from bkr.server.flask_util import Unauthorised401
from bkr.server.model import User

# deprecated
__all__ = ['Auth']
import cherrypy
from turbogears.config import get
from bkr.server.xmlrpccontroller import RPCRoot


log = logging.getLogger(__name__)

KRB_AUTH_PRINCIPAL = app.config.get("identity.krb_auth_principal")
KRB_AUTH_KEYTAB = app.config.get("identity.krb_auth_keytab")

OAUTH2_TOKEN_INFO_URL = app.config.get('identity.oauth2_token_info_url')
OAUTH2_CLIENT_ID = app.config.get('identity.oauth2_client_id')
OAUTH2_CLIENT_SECRET = app.config.get('identity.oauth2_client_secret')


@app.route('/auth/login_password', methods=['POST'])
def login_password():
    """
    Authenticates the current session using the given username and password.

    The caller may act as a proxy on behalf of another user by passing the
    *proxy_user* key. This requires that the caller has 'proxy_auth'
    permission.
    The request body must be a JSON object containing username and password.
    Proxy_user is optional.

    :jsonparam string username: Username
    :jsonparam string password: Password
    :jsonparam string proxy_user: Username on whose behalf the caller is proxying

    """

    payload = read_json_request(request)
    username = payload.get('username')
    password = payload.get('password')
    proxy_user = payload.get('proxy_user')

    user = User.by_user_name(username)
    if user is None:
        raise Unauthorised401(u'Invalid username or password')
    if not user.can_log_in():
        raise Unauthorised401(u'Invalid username or password')

    if not user.check_password(password):
        raise Unauthorised401(u'Invalid username or password')
    if proxy_user:
        if not user.has_permission(u'proxy_auth'):
            raise Unauthorised401(u'%s does not have proxy_auth permission' % user.user_name)
        proxied_user = User.by_user_name(proxy_user)
        if proxied_user is None:
            raise Unauthorised401(u'Proxy user %s does not exist' % proxy_user)
        identity.set_authentication(proxied_user, proxied_by=user)
    else:
        identity.set_authentication(user)
    return jsonify({'username': user.user_name})


@app.route('/auth/login_krbv', methods=['POST'])
def login_krbv():
    """
    Authenticates the current session using Kerberos.
    The caller may act as a proxy on behalf of another user by passing the
    *proxy_user* key. This requires that the caller has 'proxy_auth'
    permission. The request body must be a JSON object containing krb_request.
    Proxy_user is optional.

    :jsonparam base64-encoded-string krb_request: KRB_AP_REQ message containing
        client credentials, as produced by :c:func:`krb5_mk_req`
    :jsonparam string proxy_user: Username on whose behalf the caller is proxying
    """
    import krbV
    import base64

    payload = read_json_request(request)
    krb_request = payload.get('krb_request')
    proxy_user = payload.get('proxy_user')

    context = krbV.default_context()
    server_principal = krbV.Principal(name=KRB_AUTH_PRINCIPAL, context=context)
    server_keytab = krbV.Keytab(name=KRB_AUTH_KEYTAB, context=context)

    auth_context = krbV.AuthContext(context=context)
    auth_context.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
    auth_context.addrs = (
        socket.gethostbyaddr(request.remote_addr), 0, request.remote_addr, 0)

    # decode and read the authentication request
    decoded_request = base64.decodestring(krb_request)
    auth_context, opts, server_principal, cache_credentials = context.rd_req(
        decoded_request,
        server=server_principal,
        keytab=server_keytab,
        auth_context=auth_context,
        options=krbV.AP_OPTS_MUTUAL_REQUIRED)
    cprinc = cache_credentials[2]

    # remove @REALM
    username = cprinc.name.split("@")[0]
    user = User.by_user_name(username)
    if user is None:
        raise Unauthorised401(u'Invalid username')
    if not user.can_log_in():
        raise Unauthorised401(u'Invalid username')
    if proxy_user:
        if not user.has_permission(u'proxy_auth'):
            raise Unauthorised401(u'%s does not have proxy_auth permission' % user.user_name)
        proxied_user = User.by_user_name(proxy_user)
        if proxied_user is None:
            raise Unauthorised401(u'Proxy user %s does not exist' % proxy_user)
        identity.set_authentication(proxied_user, proxied_by=user)
    else:
        identity.set_authentication(user)
    return jsonify({'username': user.user_name})


@app.route('/auth/login_oauth2', methods=['POST'])
def login_oauth2():
    """
    Authenticates the current session using OAuth2.

    The caller may act as a proxy on behalf of another user by passing the
    *proxy_user* key. This requires that the caller has 'proxy_auth'
    permission.
    The request body must be a JSON object containing access_token.
    Proxy_user is optional.

    :jsonparam string access_token: The OAuth2 access token
    :jsonparam string proxy_user: Username on whose behalf the caller is proxying

    """

    payload = read_json_request(request)
    access_token = payload.get('access_token')
    proxy_user = payload.get('proxy_user')

    token_info_resp = requests.post(
        OAUTH2_TOKEN_INFO_URL,
        timeout=app.config.get('identity.soldapprovider.timeout'),
        data={'client_id': OAUTH2_CLIENT_ID,
              'client_secret': OAUTH2_CLIENT_SECRET,
              'token': access_token})
    token_info_resp.raise_for_status()
    token_info = token_info_resp.json()

    if not token_info['active']:
        raise Unauthorised401(u'Invalid token')

    if not 'https://beaker-project.org/oidc/scope' in token_info.get('scope', '').split(' '):
        raise Unauthorised401(u'Token missing required scope')

    username = token_info.get('sub')
    if not username:
        raise Unauthorised401(u'Token missing subject')

    user = User.by_user_name(username)
    if user is None:
        raise Unauthorised401(u'Invalid username')
    if not user.can_log_in():
        raise Unauthorised401(u'Invalid username')
    if proxy_user:
        if not user.has_permission(u'proxy_auth'):
            raise Unauthorised401(u'%s does not have proxy_auth permission' % user.user_name)
        proxied_user = User.by_user_name(proxy_user)
        if proxied_user is None:
            raise Unauthorised401(u'Proxy user %s does not exist' % proxy_user)
        identity.set_authentication(proxied_user, proxied_by=user)
    else:
        identity.set_authentication(user)
    return jsonify({'username': user.user_name})


@app.route('/auth/logout', methods=['POST'])
def logout():
    """
    Invalidates the current session.
    """
    identity.clear_authentication()
    return jsonify({'message': True})


@app.route('/auth/whoami', methods=['GET'])
@auth_required
def who_am_i():
    """
    Returns an JSON with information about the
    currently logged in user.
    Provided for testing purposes.

    """
    retval = {'username': identity.current.user.user_name,
              'email_address': identity.current.user.email_address}
    if identity.current.proxied_by_user is not None:
        retval['proxied_by_username'] = identity.current.proxied_by_user.user_name
    return jsonify(retval)


# deprecated
class LoginException(BX):
    pass


class Auth(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

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
                  'email_address': identity.current.user.email_address}
        if identity.current.proxied_by_user is not None:
            retval['proxied_by_username'] = identity.current.proxied_by_user.user_name
        return retval

    @cherrypy.expose
    def renew_session(self, *args, **kw):
        """
        Renew session, here to support the login method
        that was migrated from kobo.
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
    def login_oauth2(self, access_token, proxy_user=None):
        """
        Authenticates the current session using OAuth2.
        The caller may act as a proxy on behalf of another user by passing the
        *proxy_user* argument. This requires that the caller has 'proxy_auth'
        permission.
        :param access_token: The OAuth2 access token
        :type access_token: string
        :param proxy_user: username on whose behalf the caller is proxying
        :type proxy_user: string or None
        """
        token_info_resp = requests.post(
            OAUTH2_TOKEN_INFO_URL,
            timeout=get('identity.soldapprovider.timeout'),
            data={'client_id': OAUTH2_CLIENT_ID,
                  'client_secret': OAUTH2_CLIENT_SECRET,
                  'token': access_token})
        token_info_resp.raise_for_status()
        token_info = token_info_resp.json()

        if not token_info['active']:
            raise LoginException(_(u'Invalid token'))

        if not 'https://beaker-project.org/oidc/scope' in token_info.get('scope', '').split(' '):
            raise LoginException(_(u'Token missing required scope'))

        username = token_info.get('sub')
        if not username:
            raise LoginException(_(u'Token missing subject'))

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
        server_principal = krbV.Principal(name=KRB_AUTH_PRINCIPAL, context=context)
        server_keytab = krbV.Keytab(name=KRB_AUTH_KEYTAB, context=context)

        auth_context = krbV.AuthContext(context=context)
        auth_context.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
        auth_context.addrs = (
            socket.gethostbyname(cherrypy.request.remote_host), 0, cherrypy.request.remote_addr, 0)

        # decode and read the authentication request
        decoded_request = base64.decodestring(krb_request)
        auth_context, opts, server_principal, cache_credentials = context.rd_req(
            decoded_request,
            server=server_principal,
            keytab=server_keytab,
            auth_context=auth_context,
            options=krbV.AP_OPTS_MUTUAL_REQUIRED
        )
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
