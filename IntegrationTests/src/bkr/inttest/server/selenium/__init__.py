
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import time
import logging
from selenium import webdriver
from selenium.common.exceptions import ErrorInResponseException
import xmlrpclib
from urlparse import urljoin
from bkr.common.xmlrpc2 import CookieTransport
from bkr.common.xmlrpc2 import SafeCookieTransport
from bkr.inttest import get_server_base
from bkr.inttest import Process
from bkr.inttest import DatabaseTestCase
import pkg_resources

pkg_resources.require('selenium >= 2.0b2')

log = logging.getLogger(__name__)

# We track all browser instances launched by the test suite here,
# so that at the end we can check if any were leaked.
_spawned_browsers = []

class WebDriverTestCase(DatabaseTestCase):

    def get_browser(self):
        """
        Returns a new WebDriver browser instance. The browser will be cleaned
        up after the test case finishes.
        """
        profile = webdriver.FirefoxProfile()
        # clicking on element may be ignored if native events is enabled
        # https://bugzilla.redhat.com/show_bug.cgi?id=915695
        # http://code.google.com/p/selenium/issues/detail?id=2864
        profile.native_events_enabled = False

        # 2019/01/28 - Intermittent failures 'error: [Errno 111] Connection refused'
        # Issue appears to be that the server is getting saturated from all
        # the connections being created and closed by the test code. So, if
        # the call fails with a server error we wait a couple of seconds and
        # retry. If it fails a second time the retry throws an exception and
        # the test fails. Any other type of exception fails right away.
        driver = None
        try:
            driver = webdriver.Firefox(profile)
        except ErrorInResponseException as errorInResponse:
            if "Connection refused" in str(errorInResponse):
                log.debug('Connection refused when attempting to create ' +
                          'new instance of the Firefox driver')
                log.debug('Sleep for 2 seconds and retry...')
                time.sleep(2)
                driver = webdriver.Firefox(profile)
            else:
                log.debug('ErrorInResponseException raised when attempting ' +
                          'to create new instance of the Firefox driver, ' +
                          'exception text did not contain "Connection refused"')
                raise errorInResponse

        _spawned_browsers.append(driver)
        self.addCleanup(driver.quit)
        driver.implicitly_wait(15)
        driver.set_window_position(0, 0)
        driver.set_window_size(1920, 1200)
        return driver

class XmlRpcTestCase(DatabaseTestCase):

    @classmethod
    def get_server(cls):
        endpoint = urljoin(get_server_base(), 'RPC2')
        transport = endpoint.startswith('https:') and \
                SafeCookieTransport(use_datetime=True) or \
                CookieTransport(use_datetime=True)
        return xmlrpclib.ServerProxy(endpoint, transport=transport,
                allow_none=True, use_datetime=True)

processes = []

def setup_package():
    processes.extend([
        Process('Xvfb', args=['Xvfb', ':4', '-extension', 'GLX', '-noreset',
                '-listen', 'tcp', '-screen', '0', '1920x1200x24'], listen_port=6004),
    ])
    try:
        for process in processes:
            process.start()
    except:
        for process in processes:
            process.stop()
        raise
    os.environ['DISPLAY'] = ':4' # for WebDriver

def teardown_package():
    del os.environ['DISPLAY']
    for process in processes:
        process.stop()
    leaked_browsers = [b for b in _spawned_browsers if not b.binary.process.poll()]
    if leaked_browsers:
        raise RuntimeError('Test suite leaked browser instances: pid %s'
                % ','.join(str(b.binary.process.pid) for b in leaked_browsers))
