# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os
import re
import logging
import subprocess
from selenium import selenium, webdriver
import unittest
import xmlrpclib
from urlparse import urljoin
import kobo.xmlrpc
from datetime import datetime
from bkr.inttest import data_setup, get_server_base, Process
from bkr.inttest.assertions import wait_for_condition
from bkr.server.bexceptions import BX
from time import sleep
import pkg_resources

pkg_resources.require('selenium >= 2.0b2')

log = logging.getLogger(__name__)

class SeleniumTestCase(unittest.TestCase):

    BEAKER_LOGIN_USER = u'admin'
    BEAKER_LOGIN_PASSWORD = u'testing'

    @classmethod
    def wait_and_try(cls, f, wait_time=30):
        start_time = datetime.now()
        while True:
            try:
                f()
                break
            except AssertionError, e:
                current_test_time = datetime.now()
                delta = current_test_time - start_time
                if delta.seconds > wait_time:
                    raise
                else:
                    sleep(0.25)
                    pass
    @classmethod
    def wait_for_condition(cls, cond, wait_time=30):
        wait_for_condition(cond, timeout=wait_time)

    @classmethod
    def get_selenium(cls):
        cls.sel = selenium('localhost', 4444, '*chrome', get_server_base())
        return cls.sel

    @classmethod
    def logout(cls):
        sel = getattr(cls,'sel',None)
        if sel is not None:
            sel.open("")
            try:
                sel.click("link=Log out")
            except Exception, e:
                raise BX(unicode(e))
            sel.wait_for_page_to_load("30000")
            return True 
        return False

    @classmethod
    def login(cls,user=None, password=None):
        if user is None and password is None:
            user = cls.BEAKER_LOGIN_USER
            password = cls.BEAKER_LOGIN_PASSWORD
        
        sel = getattr(cls,'sel',None)
        if sel is not None:
            sel.open("")
            try:
                sel.click("link=Log in")
            except Exception, e:
                raise BX(_(unicode(e)))
            sel.wait_for_page_to_load("30000")
            sel.type("user_name", user)
            sel.type("password", password)
            sel.click("login")
            sel.wait_for_page_to_load("30000")
            return True
        return False

    def assert_system_view_text(self, field, val):
        sel = self.selenium
        text = sel.get_text("//td[preceding-sibling::"
            "th/label[@for='form_%s']]" % field)
        self.assertEqual(text.strip(), val)

class WebDriverTestCase(unittest.TestCase):

    @classmethod
    def get_browser(cls):
        p = webdriver.FirefoxProfile()
        # clicking on element may be ignored if native events is enabled
        # https://bugzilla.redhat.com/show_bug.cgi?id=915695
        # http://code.google.com/p/selenium/issues/detail?id=2864
        p.native_events_enabled = False
        b = webdriver.Firefox(p)
        b.implicitly_wait(10) # XXX is this really what we want???
        return b

class XmlRpcTestCase(unittest.TestCase):

    @classmethod
    def get_server(cls):
        endpoint = urljoin(get_server_base(), 'RPC2')
        transport = endpoint.startswith('https:') and \
                kobo.xmlrpc.SafeCookieTransport(use_datetime=True) or \
                kobo.xmlrpc.CookieTransport(use_datetime=True)
        return xmlrpclib.ServerProxy(endpoint, transport=transport,
                allow_none=True, use_datetime=True)

def jvm_version():
    popen = subprocess.Popen(['java', '-version'], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
    stdout, stderr = popen.communicate()
    version_line = stdout.splitlines()[0]
    m = re.match(r'java version "(\d)\.(\d)', version_line)
    assert m is not None, version_line
    return (int(m.group(1)), int(m.group(2)))

processes = []

def setup_package():
    assert jvm_version() >= (1, 6), 'Selenium needs JVM >= 1.6'
    if not os.path.exists('/tmp/selenium'):
        os.mkdir('/tmp/selenium')
    processes.extend([
        Process('Xvfb', args=['Xvfb', ':4', '-extension', 'GLX',
                '-screen', '0', '1024x768x24'], listen_port=6004),
        Process('selenium-server', args=['java',
                '-Djava.io.tmpdir=/tmp/selenium',
                '-jar', '/usr/local/share/selenium/selenium-server-standalone-2.35.0.jar',
                '-log', 'selenium.log'], env={'DISPLAY': ':4'},
                listen_port=4444),
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
