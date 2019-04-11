# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import base64
import os
import socket
import ssl
import threading
import logging
import time
# Make pylint2 happy
import six.moves.http_client as httplib
import six.moves.http_cookiejar as cookielib
import six.moves.xmlrpc_client as xmlrpclib
from six.moves.urllib_parse import urlparse
from six.moves.urllib import request

try:
    import kerberos

    USE_KERBEROS = True
except ImportError:
    USE_KERBEROS = False
CONNECTION_LOCK = threading.Lock()

logger = logging.getLogger(__name__)


class TimeoutHTTPConnection(httplib.HTTPConnection):

    def set_timeout(self, value):
        setattr(self, '_timeout', value)

    def connect(self):
        httplib.HTTPConnection.connect(self)
        timeout = getattr(self, "_timeout", 0)
        if timeout:
            self.sock.settimeout(timeout)


class TimeoutHTTPProxyConnection(TimeoutHTTPConnection):
    default_port = httplib.HTTPConnection.default_port

    def __init__(self, host, proxy, port=None, proxy_user=None, proxy_password=None, **kwargs):
        TimeoutHTTPConnection.__init__(self, proxy, **kwargs)
        self.proxy, self.proxy_port = self.host, self.port
        self.set_host_and_port(host, port)
        self.real_host, self.real_port = self.host, self.port
        self.proxy_user = proxy_user
        self.proxy_password = proxy_password

    def connect(self):
        # Connect to the proxy
        self.set_host_and_port(self.proxy, self.proxy_port)
        httplib.HTTPConnection.connect(self)
        self.set_host_and_port(self.real_host, self.real_port)
        timeout = getattr(self, "_timeout", 0)
        if timeout:
            self.sock.settimeout(timeout)

    def putrequest(self, method, url, skip_host=0, skip_accept_encoding=0):
        host = self.real_host
        if self.default_port != self.real_port:
            host = host + ':' + str(self.real_port)
        url = "http://%s%s" % (host, url)
        httplib.HTTPConnection.putrequest(self, method, url)
        self._add_auth_proxy_header()

    def _add_auth_proxy_header(self):
        if not self.proxy_user:
            return
        userpass = "%s:%s" % (self.proxy_user, self.proxy_password)
        enc_userpass = base64.encodebytes(userpass).strip()  # pylint: disable=no-member
        self.putheader("Proxy-Authorization", "Basic %s" % enc_userpass)

    def set_host_and_port(self, host, port):
        if hasattr(self, "_set_hostport"):  # Python < 2.7.7
            self._set_hostport(host, port)  # pylint: disable=no-member
        else:
            (self.host, self.port) = self._get_hostport(host, port)


class TimeoutHTTPSProxyConnection(TimeoutHTTPProxyConnection):
    default_port = httplib.HTTPSConnection.default_port

    def __init__(self, host, proxy, port=None, proxy_user=None,
                 proxy_password=None, cert_file=None, key_file=None, **kwargs):
        TimeoutHTTPProxyConnection.__init__(self, host, proxy, port,
                                            proxy_user, proxy_password, **kwargs)
        self.cert_file = cert_file
        self.key_file = key_file
        self.connect()

    def connect(self):
        TimeoutHTTPProxyConnection.connect(self)
        host = "%s:%s" % (self.real_host, self.real_port)
        TimeoutHTTPConnection.putrequest(self, "CONNECT", host)
        self._add_auth_proxy_header()
        TimeoutHTTPConnection.endheaders(self)

        class MyHTTPSResponse(httplib.HTTPResponse):
            def begin(self):
                httplib.HTTPResponse.begin(self)
                self.will_close = 0

        response_class = self.response_class
        self.response_class = MyHTTPSResponse
        response = httplib.HTTPConnection.getresponse(self)
        self.response_class = response_class
        response.close()
        if response.status != 200:
            self.close()
            raise socket.error(1001, response.status, response.msg)

        self.sock = ssl.wrap_socket(self.sock, keyfile=self.key_file, certfile=self.cert_file)

    def putrequest(self, method, url, skip_host=0, skip_accept_encoding=0):
        return TimeoutHTTPConnection.putrequest(self, method, url)


class TimeoutHTTPSConnection(httplib.HTTPSConnection):

    def set_timeout(self, value):
        setattr(self, '_timeout', value)

    def connect(self):
        timeout = getattr(self, '_timeout', 0)
        if timeout:
            self.timeout = timeout
        httplib.HTTPSConnection.connect(self)


class TimeoutProxyHTTPS(TimeoutHTTPSProxyConnection):
    _connection_class = TimeoutHTTPSProxyConnection

    def __init__(self, host='', proxy='', port=None, proxy_user=None,
                 proxy_password=None, cert_file=None, key_file=None, **kwargs):
        if port == 0:
            port = None
        TimeoutHTTPSProxyConnection.__init__(self, host, proxy, port, proxy_user, proxy_password,
                                             cert_file, key_file, **kwargs)


class CookieResponse(object):
    """
    Fake response class for cookie extraction.
    """

    def __init__(self, headers):
        self.headers = headers

    def info(self):
        """
        Pass response headers to cookie jar.
        """
        return self.headers


class CookieTransport(xmlrpclib.Transport):
    """
    Cookie enabled XML-RPC transport.

    USAGE:
    >>> import xmlrpc.client
    >>> from bkr.common.xmlrpc import CookieTransport
    >>> client = xmlrpc.client.ServerProxy("http://<server>/xmlrpc", transport=CookieTransport())

    For https:// connections use SafeCookieTransport() instead.
    """

    scheme = "http"

    def __init__(self, *args, **kwargs):
        cookiejar = kwargs.pop("cookiejar", None)
        self.timeout = kwargs.pop("timeout", 0)
        self.proxy_config = self._get_proxy(**kwargs)
        self.no_proxy = os.environ.get("no_proxy", "").lower().split(',')
        self.verbose = 0
        self.cookie_request = None

        xmlrpclib.Transport.__init__(self, *args, **kwargs)

        self.cookiejar = cookiejar or cookielib.CookieJar()

        if hasattr(self.cookiejar, "load"):
            if not os.path.exists(self.cookiejar.filename):
                if hasattr(self.cookiejar, "save"):
                    self.cookiejar.save(self.cookiejar.filename)
            self.cookiejar.load(self.cookiejar.filename)

    def _get_proxy(self, **kwargs):
        """
        Return dict with appropriate proxy settings
        """
        proxy = None
        proxy_user = None
        proxy_password = None

        if kwargs.get("proxy", None):
            # Use proxy from __init__ params
            proxy = kwargs["proxy"]
            if kwargs.get("proxy_user", None):
                proxy_user = kwargs["proxy_user"]
                if kwargs.get("proxy_password", None):
                    proxy_password = kwargs["proxy_user"]
        else:
            # Try to get proxy settings from environmental vars
            if self.scheme == "http" and os.environ.get("http_proxy", None):
                proxy = os.environ["http_proxy"]
            elif self.scheme == "https" and os.environ.get("https_proxy", None):
                proxy = os.environ["https_proxy"]

        if proxy:
            # Parse proxy address
            # e.g. http://user:password@proxy.company.com:8001/foo/bar

            # Get raw location without path
            location = urlparse(proxy)[1]
            if not location:
                # proxy probably doesn't have a protocol in prefix
                location = urlparse("http://%s" % proxy)[1]

            # Parse out username and password if present
            if '@' in location:
                userpas, location = location.split('@', 1)
                if userpas and location and not proxy_user:
                    # Set proxy user only if proxy_user is not set yet
                    proxy_user = userpas
                    if ':' in userpas:
                        proxy_user, proxy_password = userpas.split(':', 1)

            proxy = location

        proxy_settings = {
            "proxy": proxy,
            "proxy_user": proxy_user,
            "proxy_password": proxy_password,
        }

        return proxy_settings

    def make_connection(self, host):

        host.lower()

        if ':' in host:
            # Remove port from the host
            host_ = host.split(':')[0]
        else:
            host_ = "%s:%s" % (host, TimeoutHTTPProxyConnection.default_port)

        if self.proxy_config["proxy"] and host not in self.no_proxy and host_ not in self.no_proxy:
            CONNECTION_LOCK.acquire()
            host, _, _ = self.get_host_info(host)
            conn = TimeoutProxyHTTPS(host, **self.proxy_config)
            conn.set_timeout(self.timeout)
            CONNECTION_LOCK.release()
            return conn

        CONNECTION_LOCK.acquire()
        # this disables connection caching which causes a race condition when running in threads
        self._connection = (None, None)
        conn = xmlrpclib.Transport.make_connection(self, host)
        CONNECTION_LOCK.release()

        if self.timeout:
            conn.timeout = self.timeout

        return conn

    def send_cookies(self, connection):
        """
        Add cookies to the header.
        """
        self.cookiejar.add_cookie_header(self.cookie_request)

        for header, value in self.cookie_request.header_items():
            if header.startswith("Cookie"):
                connection.putheader(header, value)

    def send_headers(self, connection, headers):

        for key, val in headers:
            connection.putheader(key, val)

        self.send_cookies(connection)

    def _save_cookies(self, headers, cookie_request):
        cookie_response = CookieResponse(headers)
        self.cookiejar.extract_cookies(cookie_response, cookie_request)
        if hasattr(self.cookiejar, "save"):
            self.cookiejar.save(self.cookiejar.filename)

    @staticmethod
    def _kerberos_client_request(host, handler, errcode, errmsg, headers):
        """Kerberos auth - create a client request string"""

        # check if "Negotiate" challenge is present in headers
        negotiate = [i.lower() for i in headers.get("WWW-Authenticate", "").split(", ")]
        if "negotiate" not in negotiate:
            # negotiate not supported, raise 401 error
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # initialize GSSAPI
        service = "HTTP@%s" % host
        rc, vc = kerberos.authGSSClientInit(service)
        if rc != 1:
            errmsg = "KERBEROS: Could not initialize GSSAPI"
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # do a client step
        rc = kerberos.authGSSClientStep(vc, "")
        if rc != 0:
            errmsg = "KERBEROS: Client step failed"
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        return vc, kerberos.authGSSClientResponse(vc)

    @staticmethod
    def _kerberos_verify_response(vc, host, handler, headers):
        """Kerberos auth - verify client identity"""
        # verify that headers contain WWW-Authenticate header
        auth_header = headers.get("WWW-Authenticate", None)
        if auth_header is None:
            errcode = 401
            errmsg = "KERBEROS: No WWW-Authenticate header in second HTTP response"
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # verify that WWW-Authenticate contains Negotiate
        splits = auth_header.split(" ", 1)
        if (len(splits) != 2) or (splits[0].lower() != "negotiate"):
            errcode = 401
            errmsg = "KERBEROS: Incorrect WWW-Authenticate header in second HTTP response: %s" % auth_header
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # do another client step to verify response from server
        errmsg = "KERBEROS: Could not verify server WWW-Authenticate header in second HTTP response"
        try:
            rc = kerberos.authGSSClientStep(vc, splits[1])
            if rc == -1:
                errcode = 401
                raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)
        except kerberos.GSSError as ex:
            errcode = 401
            errmsg += ": %s/%s" % (ex[0][0], ex[1][0])
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

        # cleanup
        rc = kerberos.authGSSClientClean(vc)
        if rc != 1:
            errcode = 401
            errmsg = "KERBEROS: Could not clean-up GSSAPI: %s/%s" % (ex[0][0], ex[1][0])
            raise xmlrpclib.ProtocolError(host + handler, errcode, errmsg, headers)

    def single_request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        request_url = "%s://%s/" % (self.scheme, host)
        self.cookie_request = request.Request(request_url)
        self.verbose = verbose

        try:

            http_con = self.send_request(host, handler, request_body, False)  # pylint: disable=too-many-function-args
            self._extra_headers = []
            response = http_con.getresponse()

            if response.status == 401 and USE_KERBEROS:
                vc, challenge = self._kerberos_client_request(host, handler, response.status,
                                                              response.reason, response.msg)

                # discard any response data
                if response.getheader("content-length", 0):
                    response.read()

                # retry the original request & add the Authorization header:
                self._extra_headers = [("Authorization", "Negotiate %s" % challenge)]
                http_con = self.send_request(host, handler, request_body, verbose)  # pylint: disable=too-many-function-args
                self._extra_headers = []

                response = http_con.getresponse()
                self._kerberos_verify_response(vc, host, handler, response.msg)

            if response.status == 200:
                self.verbose = verbose
                self._save_cookies(response.msg, self.cookie_request)
                return self.parse_response(response)
        except xmlrpclib.Fault:
            raise
        except Exception:
            # All unexpected errors leave connection in
            # a strange state, so we clear it.
            if hasattr(self, 'close'):
                self.close()
            raise

        # discard any response data and raise exception
        if response.getheader("content-length", 0):
            response.read()
        raise xmlrpclib.ProtocolError(host + handler, response.status, response.reason,
                                      response.msg)


class SafeCookieTransport(xmlrpclib.SafeTransport, CookieTransport):
    """
    Cookie enabled XML-RPC transport over HTTPS.

    USAGE: see CookieTransport
    """

    scheme = "https"

    def __init__(self, *args, **kwargs):
        # SafeTransport.__init__ does this but we can't call that because we
        # have an inheritance diamond and these are old-style classes...
        self.context = kwargs.pop('context', None)
        CookieTransport.__init__(self, *args, **kwargs)

    def make_connection(self, host):

        host.lower()

        if ':' in host:
            # Remove port from the host
            host_ = host.split(':')[0]
        else:
            host_ = "%s:%s" % (host, TimeoutHTTPSProxyConnection.default_port)

        if self.proxy_config["proxy"] and host not in self.no_proxy and host_ not in self.no_proxy:
            CONNECTION_LOCK.acquire()
            host, _, _ = self.get_host_info(host)
            conn = TimeoutProxyHTTPS(host, **self.proxy_config)
            conn.set_timeout(self.timeout)
            CONNECTION_LOCK.release()

            return conn

        CONNECTION_LOCK.acquire()
        self._connection = (None, None)
        conn = xmlrpclib.SafeTransport.make_connection(self, host)
        if self.timeout:
            conn.timeout = self.timeout
        CONNECTION_LOCK.release()

        return conn


def retry_request_decorator(transport_class):
    """
    Use this class decorator on a Transport
    to retry requests which failed on socket errors.
    """

    class RetryTransportClass(transport_class):
        def __init__(self, *args, **kwargs):
            self.retry_count = kwargs.pop("retry_count", 5)
            self.retry_timeout = kwargs.pop("retry_timeout", 30)
            transport_class.__init__(self, *args, **kwargs)

        def request(self, *args, **kwargs):
            if self.retry_count == 0:
                return transport_class.request(self, *args, **kwargs)

            for i in list(range(self.retry_count + 1)):
                try:
                    result = transport_class.request(self, *args, **kwargs)
                    return result
                except KeyboardInterrupt:
                    raise
                except (socket.error, socket.herror, socket.gaierror, socket.timeout) as ex:
                    if hasattr(self, 'close'):
                        self.close()
                    if i >= self.retry_count:
                        raise
                    retries_left = self.retry_count - i
                    # 1 retry left / X retries left
                    retries = (retries_left == 1 and "retry" or "retries")
                    logger.warning("XML-RPC connection to %s failed: %s, %d %s left",
                                   args[0], " ".join(ex.args[1:]), retries_left, retries,
                                   exc_info=True)
                    time.sleep(self.retry_timeout)

    RetryTransportClass.__name__ = transport_class.__name__
    RetryTransportClass.__doc__ = transport_class.__name__
    return RetryTransportClass
