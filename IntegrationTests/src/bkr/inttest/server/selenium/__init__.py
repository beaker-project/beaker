
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os
import re
import logging
import subprocess
from selenium import webdriver
import unittest2 as unittest
import xmlrpclib
from urlparse import urljoin
from bkr.common.xmlrpc import CookieTransport, SafeCookieTransport
from datetime import datetime
from bkr.inttest import data_setup, get_server_base, Process
from bkr.inttest.assertions import wait_for_condition
from bkr.server.bexceptions import BX
from time import sleep
import pkg_resources

pkg_resources.require('selenium >= 2.0b2')

log = logging.getLogger(__name__)

# We track all browser instances launched by the test suite here,
# so that at the end we can check if any were leaked.
_spawned_browsers = []

class WebDriverTestCase(unittest.TestCase):

    def get_browser(self):
        """
        Returns a new WebDriver browser instance. The browser will be cleaned 
        up after the test case finishes.
        """
        p = webdriver.FirefoxProfile()
        # clicking on element may be ignored if native events is enabled
        # https://bugzilla.redhat.com/show_bug.cgi?id=915695
        # http://code.google.com/p/selenium/issues/detail?id=2864
        p.native_events_enabled = False
        b = webdriver.Firefox(p)
        _spawned_browsers.append(b)
        self.addCleanup(b.quit)
        b.implicitly_wait(10) # XXX is this really what we want???
        b.set_window_position(0, 0)
        b.set_window_size(1920, 1200)
        return b

class XmlRpcTestCase(unittest.TestCase):

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
                '-screen', '0', '1920x1200x24'], listen_port=6004),
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
