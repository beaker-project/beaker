# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import os
from urllib.parse import urljoin

import requests
from requests import Response
from requests.auth import HTTPBasicAuth

from bkr.common import __version__
from bkr.common.pyconfig import PyConfigParser

log = logging.getLogger(__name__)


class RestAPI:
    default_headers = {"Accept": "application/json", "X-Beaker-Version": __version__}

    def __init__(
        self,
        api_url,
        username=None,
        password=None,
        timeout=120,
        verify_ssl=True,
        ca_cert=None,
        session=None,
        kerberos=False,
        cookies=None,
        raw_mode=False,
    ):

        self.api_url = api_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.ca_cert = ca_cert
        self.session = session or requests.Session()
        self.kerberos = kerberos
        self.cookies = cookies
        self.raw_mode = raw_mode

        self.create_auth_session()

    def create_auth_session(self):
        if self.username and self.password:
            self._basic_auth_session()
        elif self.kerberos:
            self._kerberos_session()
        elif self.cookies:
            self.session.cookies = self.cookies

    def _basic_auth_session(self):
        self.session.auth = HTTPBasicAuth(self.username, self.password)

    def _kerberos_session(self):
        """Create session w/ HTTPKerberosAuth"""

        # This is quite simple how we should do.
        raise NotImplementedError

    def close(self):
        return self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @staticmethod
    def _handle_response(res):
        try:
            return res.json()
        except ValueError:
            log.debug("Response has no content")
            return None
        except Exception as e:
            log.error(e)
            return None

    def request(
        self,
        method="GET",
        path="/",
        data=None,
        json=None,
        params=None,
        headers=None,
    ):

        url = urljoin(self.api_url, path)

        headers = headers or self.default_headers
        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            json=json,
            timeout=self.timeout,
            verify=self.verify_ssl,
            params=params,
        )

        log.debug(
            "HTTP: {} {} -> {} {}".format(
                method, path, response.status_code, response.reason
            )
        )
        log.debug("HTTP: Response text -> {}".format(response.text))
        if self.raw_mode:
            return response

        response.raise_for_status()
        return response

    def post(
        self,
        path,
        data=None,
        json=None,
        headers=None,
        params=None,
        raw_mode=False,
    ):
        res = self.request("POST", path, data, json, params, headers)
        if raw_mode or self.raw_mode:
            return res

        return self._handle_response(res)

    def get(self, path, data=None, params=None, headers=None, raw_mode=False):
        # XXX: I guess we should play here more w/ params to help properly build final URLs
        res = self.request("GET", path=path, data=data, params=params, headers=headers)
        if raw_mode or self.raw_mode:
            return res
        return self._handle_response(res)

    def put(
        self, path, data=None, json=None, headers=None, params=None, raw_mode=False
    ):
        res = self.request(
            "PUT",
            path=path,
            data=data,
            json=json,
            headers=headers,
            params=params,
        )
        if raw_mode or self.raw_mode:
            return res
        return self._handle_response(res)

    def delete(self, path, data=None, headers=None, params=None, raw_mode=False):

        res = self.request(
            "DELETE",
            path=path,
            data=data,
            headers=headers,
            params=params,
        )
        if raw_mode or self.raw_mode:
            return res
        return self._handle_response(res)

    def patch(
        self, path, data=None, json=None, headers=None, params=None, raw_mode=False
    ):
        res = self.request(
            "PATCH", path=path, data=data, json=json, headers=headers, params=params
        )
        if raw_mode or self.raw_mode:
            return res
        return self._handle_response(res)


# This should be in separate package in future.
# Wrap whole API to Python objects to avoid direct calls.
# However, API is really unstable, therefore it is not worth to do it right now.
class BeakerAPI(RestAPI):
    @classmethod
    def from_config(
        cls,
        conf,
        auto_login=True,
        timeout=120,
        session=None,
        kerberos=False,
        cookies=None,
        raw_mode=False,
        **kwargs,
    ):
        _conf = PyConfigParser()

        # Load default configuration
        default_config = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "default.conf")
        )
        _conf.load_from_file(default_config)

        # Update configuration w/ user defined
        if conf is not None:
            _conf.load_from_conf(conf)

        # Update w/ kwargs
        _conf.load_from_dict(kwargs)

        # Initialize BeakerAPI
        api_url = _conf["HUB_URL"]
        api_url = api_url if api_url.endswith("/") else api_url + "/"
        auth_method = _conf.get("AUTH_METHOD")
        username = _conf.get("USERNAME")
        password = _conf.get("PASSWORD")
        proxy_user = _conf.get("PROXY_USER")
        ca_cert = _conf.get("CA_CERT", None)
        ssl_verify = _conf.get("SSL_VERIFY", True)

        beaker_api = cls(
            api_url,
            username,
            password,
            timeout,
            ssl_verify,
            ca_cert,
            session,
            kerberos,
            cookies,
            raw_mode,
        )
        if auto_login:
            beaker_api.login(auth_method, proxy_user)

        return beaker_api

    def login(self, method: str = "password", proxy_user: str = ""):
        login_method = getattr(self, f"_login_{method}")
        login_method(proxy_user)

    def _login_password(self, proxy_user: str = ""):
        res: Response = self.post(
            "/auth/login", data={"proxy_user": proxy_user} if proxy_user else {}
        )
        if self.raw_mode:
            res.raise_for_status()

    def _login_krbv(self, proxy_user: str = ""):
        raise NotImplementedError


if __name__ == "__main__":
    BeakerAPI.from_config(None)
