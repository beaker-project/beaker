# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Mostly copy and pasted from kobo.client.__init__ (version 0.4.2-1)
# Removed upload_task_log() and upload_file()
import os
import base64
import ssl
import xmlrpclib
import urlparse
import tempfile
from bkr.common.pyconfig import PyConfigParser, ImproperlyConfigured
from bkr.common.xmlrpc import CookieTransport, SafeCookieTransport, \
    retry_request_decorator

class AuthenticationError(Exception):
    """Authentication failed for some reason."""
    pass
class HubProxy(object):
    """A Hub client (thin ServerProxy wrapper)."""

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
            else:
                TransportClass = retry_request_decorator(CookieTransport)
            self._transport = TransportClass(**transport_args)

        self._hub = xmlrpclib.ServerProxy(
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
        except Exception, ex:
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

    def _login_worker_key(self):
        """Login using worker key."""
        worker_key = self._conf.get("WORKER_KEY")
        if not worker_key:
            raise AuthenticationError("WORKER_KEY is not set")
        self._hub.auth.login_worker_key(worker_key)

    def _login_krbv(self):
        """Login using kerberos credentials (uses python-krbV)."""

        def get_server_principal(service=None, realm=None):
            """Convert hub url to kerberos principal."""
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

        import krbV
        ctx = krbV.default_context()

        if ccache is not None:
            ccache = krbV.CCache(name='FILE:' + ccache, context=ctx)
        elif keytab is not None:
            # If we will be init'ing the ccache using a keytab, we need to 
            # always avoid using the default shared ccache, as a workaround for 
            # a race condition in krb5_cc_initialize() between unlink() and open()
            # (see RHBZ#1313580).
            ccache_tmpfile = tempfile.NamedTemporaryFile(prefix='krb5cc_bkr_')
            ccache = krbV.CCache(name='FILE:' + ccache_tmpfile.name, context=ctx)
        else:
            ccache = ctx.default_ccache()

        if principal is not None:
            if keytab is not None:
                cprinc = krbV.Principal(name=principal, context=ctx)
                keytab = krbV.Keytab(name=keytab, context=ctx)
                ccache.init(cprinc)
                ccache.init_creds_keytab(principal=cprinc, keytab=keytab)
            else:
                raise ImproperlyConfigured("Cannot specify a principal without a keytab")
        else:
            # connect using existing credentials
            cprinc = ccache.principal()

        sprinc = krbV.Principal(name=get_server_principal(service=service, realm=realm), context=ctx)

        ac = krbV.AuthContext(context=ctx)
        ac.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
        ac.rcache = ctx.default_rcache()

        # create and encode the authentication request
        try:
            ac, req = ctx.mk_req(server=sprinc, client=cprinc, auth_context=ac, ccache=ccache, options=krbV.AP_OPTS_MUTUAL_REQUIRED)
        except krbV.Krb5Error, ex:
            if getattr(ex, "err_code", None) == -1765328377:
                ex.message += ". Make sure you correctly set KRB_REALM (current value: %s)." % realm
                ex.args = (ex.err_code, ex.message)
            raise ex
        req_enc = base64.encodestring(req)

        self._hub.auth.login_krbv(req_enc, proxyuser)
