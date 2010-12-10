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
import logging
import subprocess
import signal
import time
import turbogears.config
from selenium import selenium
import unittest
import threading
import xmlrpclib
from urlparse import urljoin
import kobo.xmlrpc
import bkr.server.test
from bkr.server.bexceptions import BX

log = logging.getLogger(__name__)

class SeleniumTestCase(unittest.TestCase):

    BEAKER_LOGIN_USER = 'admin'
    BEAKER_LOGIN_PASSWORD = 'testing'

    @classmethod
    def get_selenium(cls):
        cls.sel = selenium('localhost', 4444, '*chrome',
                bkr.server.test.get_server_base())
        return cls.sel

    @classmethod
    def logout(cls):
        sel = getattr(cls,'sel',None)
        if sel is not None:
            sel.open("")
            try:
                sel.click("link=Logout")
            except Exception, e:
                raise BX(unicode(e))
            sel.wait_for_page_to_load("3000")
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
                sel.click("link=Login")
            except Exception, e:
                raise BX(_(e))
            sel.wait_for_page_to_load("3000")
            sel.type("user_name", user)
            sel.type("password", password)
            sel.click("login")
            sel.wait_for_page_to_load("3000")
            return True
        return False

class XmlRpcTestCase(unittest.TestCase):

    @classmethod
    def get_server(cls):
        endpoint = urljoin(bkr.server.test.get_server_base(), 'RPC2')
        transport = endpoint.startswith('https:') and \
                kobo.xmlrpc.SafeCookieTransport() or \
                kobo.xmlrpc.CookieTransport()
        return xmlrpclib.ServerProxy(endpoint, transport=transport,
                allow_none=True)

def check_listen(port):
    """
    Returns True iff any process on the system is listening
    on the given TCP port.
    """
    # with newer lsof we could just use -sTCP:LISTEN,
    # but RHEL5's lsof is too old so we have to filter for LISTEN state ourselves
    output, _ = subprocess.Popen(['/usr/sbin/lsof', '-iTCP:%d' % port],
            stdout=subprocess.PIPE).communicate()
    for line in output.splitlines():
        if '(LISTEN)' in line:
            return True
    return False

class Process(object):
    """
    Thin wrapper around subprocess.Popen which supports starting and killing 
    the process in setup/teardown.
    """

    def __init__(self, name, args, env=None, listen_port=None,
            stop_signal=signal.SIGTERM):
        self.name = name
        self.args = args
        self.env = env
        self.listen_port = listen_port
        self.stop_signal = stop_signal

    def start(self):
        log.info('Spawning %s: %s %r', self.name, ' '.join(self.args), self.env)
        env = dict(os.environ)
        if self.env:
            env.update(self.env)
        self.popen = subprocess.Popen(self.args, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, env=env)
        CommunicateThread(popen=self.popen).start()
        if self.listen_port:
            self._wait_for_listen(self.listen_port)

    def _wait_for_listen(self, port):
        """
        Blocks until some process on the system is listening
        on the given TCP port.
        """
        # XXX is there a better way to do this?
        for i in range(20):
            log.info('Waiting for %s to listen on port %d', self.name, port)
            if check_listen(self.listen_port):
                return
            time.sleep(1)
        raise RuntimeError('Gave up waiting for LISTEN %d' % port)

    def stop(self):
        if not hasattr(self, 'popen'):
            log.warning('%s never started, not killing', self.name)
        elif self.popen.poll() is not None:
            log.warning('%s (pid %d) already dead, not killing', self.name, self.popen.pid)
        else:
            log.info('Sending signal %r to %s (pid %d)',
                    self.stop_signal, self.name, self.popen.pid)
            os.kill(self.popen.pid, self.stop_signal)
            self.popen.wait()

class CommunicateThread(threading.Thread):
    """
    Nose has support for capturing stdout during tests, by fiddling with sys.stdout.
    Subprocesses' stdout streams won't be captured that way, however. So for each subprocess
    one of these threads will read from its stdout and write back to sys.stdout
    for nose to capture.
    """

    def __init__(self, popen, **kwargs):
        super(CommunicateThread, self).__init__(**kwargs)
        self.daemon = True
        self.popen = popen

    def run(self):
        while True:
            data = self.popen.stdout.readline()
            if not data: break
            sys.stdout.write(data)

processes = []

def setup_package():
    if not os.path.exists('/tmp/selenium'):
        os.mkdir('/tmp/selenium')
    processes.extend([
        Process('Xvfb', args=['Xvfb', ':4', '-fp', '/usr/share/X11/fonts/misc',
                '-screen', '0', '1024x768x24']),
        Process('selenium-server', args=['java',
                '-Djava.io.tmpdir=/tmp/selenium',
                '-jar', '/usr/local/share/selenium/selenium-server-1.0.3/selenium-server.jar',
                '-log', 'selenium.log'], env={'DISPLAY': ':4'},
                listen_port=4444),
    ])
    if 'BEAKER_SERVER_BASE_URL' not in os.environ:
        # need to start the server ourselves
        processes.extend([
            Process('beaker', args=['./start-server.py', bkr.server.test.CONFIG_FILE],
                    listen_port=turbogears.config.get('server.socket_port'),
                    stop_signal=signal.SIGINT)
        ])
    try:
        for process in processes:
            process.start()
    except:
        for process in processes:
            process.stop()
        raise

def teardown_package():
    for process in processes:
        process.stop()
