# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import base64
import os
import tempfile

import gssapi
import six
import ssl
from six.moves import urllib_parse as urlparse
from six.moves import xmlrpc_client

from bkr.common.pyconfig import PyConfigParser, ImproperlyConfigured

if six.PY2:
    from bkr.common.xmlrpc2 import CookieTransport, SafeCookieTransport, retry_request_decorator
if six.PY3:
    from bkr.common.xmlrpc3 import CookieTransport, SafeCookieTransport, retry_request_decorator


class AuthenticationError(Exception):
    """
    Authentication failed for some reason.
    """
    pass


class HubProxy(object):
    """
    A Hub client (thin ServerProxy wrapper).
    """

    def __init__(self, conf, client_type=None, logger=None, transport=None,
            auto_login=True, timeout=120, **kwargs):
        self._conf = PyConfigParser()
        self._hub = None

        # load default config
        default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
        self._conf.load_from_file(default_config)

        # update config with another one
        if conf is not None:
            self._conf.load_from_conf(conf)

        # update config with kwargs
        self._conf.load_from_dict(kwargs)

        # initialize properties
        self._client_type = client_type or "client"
        self._hub_url = self._conf["HUB_URL"]
        self._auth_method = self._conf["AUTH_METHOD"]
        self._logger = logger
        self._logged_in = False

        if transport is not None:
            self._transport = transport
        else:
            transport_args = {'timeout': timeout}
            if self._hub_url.startswith("https://"):
                TransportClass = retry_request_decorator(SafeCookieTransport)
                if hasattr(ssl, 'create_default_context') and self._conf.get('CA_CERT'):
                    ssl_context = ssl.create_default_context()
                    ssl_context.load_verify_locations(cafile=self._conf['CA_CERT'])
                    transport_args['context'] = ssl_context
                elif (hasattr(ssl, '_create_unverified_context')
                      and not self._conf.get('SSL_VERIFY', True)):
                    # Python 2.6 doesn't have context argument for xmlrpclib.ServerProxy
                    # therefore transport needs to be modified
                    ssl_context = ssl._create_unverified_context()
                    transport_args['context'] = ssl_context

            else:
                TransportClass = retry_request_decorator(CookieTransport)
            self._transport = TransportClass(**transport_args)

        self._hub = xmlrpc_client.ServerProxy(
                "%s/%s/" % (self._hub_url, self._client_type),
                allow_none=True, transport=self._transport,
                verbose=self._conf.get("DEBUG_XMLRPC"))
        if auto_login:
            self._login()

    def __del__(self):
        if hasattr(self._transport, "retry_count"):
            self._transport.retry_count = 0

    def __getattr__(self, name):
        try:
            return getattr(self._hub, name)
        except:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))

    def _login(self, force=False):
        """Login to the hub.
        - self._hub instance is created in this method
        - session information is stored in a cookie in self._transport
        """
        if self._auth_method == "none" or not self._auth_method:
            return

        login_method_name = "_login_%s" % self._auth_method
        if not hasattr(self, login_method_name):
            raise ImproperlyConfigured("Unknown authentication method: %s" % self._auth_method)

        self._logger and self._logger.info("Creating new session...")
        try:
            login_method = getattr(self, login_method_name)
            login_method()
            self._logged_in = True
        except KeyboardInterrupt:
            raise
        except Exception as ex:
            self._logger and self._logger.error("Failed to create new session: %s" % ex)
            raise
        else:
            self._logger and self._logger.info("New session created.")

    def _logout(self):
        """No-op for backwards compatibility."""
        pass

    def _login_password(self):
        """Login using username and password."""
        username = self._conf.get("USERNAME")
        password = self._conf.get("PASSWORD")
        proxyuser = self._conf.get("PROXY_USER")
        if not username:
            raise AuthenticationError("USERNAME is not set")
        self._hub.auth.login_password(username, password, proxyuser)

    def _login_oauth2(self):
        """Login using OAuth2 access token."""
        access_token = self._conf.get("ACCESS_TOKEN")
        if not access_token:
            raise AuthenticationError("ACCESS_TOKEN is not set")
        self._hub.auth.login_oauth2(access_token)

    def _login_krbv(self):
        """
        Login using kerberos credentials (uses python-gssapi).
        """

        def get_server_principal(service=None, realm=None):
            """
            Convert hub url to kerberos principal.
            """
            hostname = urlparse.urlparse(self._hub_url)[1]
            # remove port from hostname
            hostname = hostname.split(":")[0]

            if realm is None:
                # guess realm: last two parts from hostname
                realm = ".".join(hostname.split(".")[-2:]).upper()
            if service is None:
                service = "HTTP"
            return '%s/%s@%s' % (service, hostname, realm)

        # read default values from settings
        principal = self._conf.get("KRB_PRINCIPAL")
        keytab = self._conf.get("KRB_KEYTAB")
        service = self._conf.get("KRB_SERVICE")
        realm = self._conf.get("KRB_REALM")
        ccache = self._conf.get("KRB_CCACHE")
        proxyuser = self._conf.get("PROXY_USER")
        krb5kdc_err_s_principal_unknown = 2529638919  # Server not found in Kerberos database

        name = None
        if principal:
            name = gssapi.Name(principal, gssapi.NameType.kerberos_principal)

        store = None  # Default ccache
        if keytab:
            # Make sure we are using always APP ccache or user specified ccache
            # instead of MIT krb5 default one with keytabs. Default ccache can be occupied by
            # system application
            store = {'client_keytab': keytab,
                     'ccache': ccache or tempfile.NamedTemporaryFile(prefix='krb5cc_bkr_').name}
        elif ccache:
            store = {'ccache': ccache}

        creds = gssapi.Credentials(name=name, store=store, usage='initiate')

        target_name = gssapi.Name(get_server_principal(service, realm))

        try:
            res = gssapi.raw.init_sec_context(target_name, creds, flags=(
                    gssapi.RequirementFlag.out_of_sequence_detection |
                    gssapi.RequirementFlag.replay_detection |
                    gssapi.RequirementFlag.mutual_authentication |
                    # This is a hack which causes GSSAPI to give us back a raw
                    # KRB_AP_REQ token value, without GSSAPI header wrapping, which
                    # is what the Beaker server is expecting in auth.login_krbv.
                    gssapi.RequirementFlag.dce_style)
            )
        except gssapi.raw.GSSError as ex:
            if ex.min_code == krb5kdc_err_s_principal_unknown:  # pylint: disable=no-member
                ex.message += ". Make sure you correctly set KRB_REALM (current value: %s)." % realm
                ex.args = (ex.message, )
            raise ex
        if six.PY2:
            req_enc = base64.encodestring(res.token)
        else:
            req_enc = base64.encodebytes(res.token)  # pylint: disable=maybe-no-member
        try:
            req_enc = str(req_enc, 'utf-8')  # bytes to string
        except TypeError:
            pass
        self._hub.auth.login_krbv(req_enc, proxyuser)
