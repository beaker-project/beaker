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

import os
import logging
import subprocess
import signal
import time

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('bkr.server.seleniumtests.__init__')

class Process(object):
    """
    Thin wrapper around subprocess.Popen which supports starting and killing 
    the process in setup/teardown.
    """

    def __init__(self, name, args, env=None, startup_delay=0):
        self.name = name
        self.args = args
        self.env = env
        self.startup_delay = startup_delay

    def start(self):
        log.info('Spawning %s: %s %r', self.name, ' '.join(self.args), self.env)
        env = dict(os.environ)
        if self.env:
            env.update(self.env)
        self.popen = subprocess.Popen(self.args, env=env)
        if self.startup_delay:
            time.sleep(self.startup_delay) # TODO use a real condition here!

    def stop(self, signal=signal.SIGTERM):
        if self.popen.poll() is not None:
            log.warning('%s (pid %d) already dead, not killing', self.name, self.popen.pid)
        else:
            log.info('Sending %r to %s (pid %d)', signal, self.name, self.popen.pid)
            os.kill(self.popen.pid, signal)
            self.popen.wait()

xvfb = Process('Xvfb', args=['Xvfb', ':4', '-fp', '/usr/share/X11/fonts/misc',
        '-screen', '0', '1024x768x24'])
selenium_server = Process('selenium-server', args=['java', '-jar',
        '/opt/selenium/selenium-server-1.0.3/selenium-server.jar',
        '-log', 'selenium.log'], env={'DISPLAY': ':4'}, startup_delay=10)
beaker = Process('beaker', args=['./start-server.py', 'test.cfg'],
        startup_delay=2)

def setup_package():
    xvfb.start()
    selenium_server.start()
    beaker.start()

def teardown_package():
    beaker.stop(signal.SIGINT)
    selenium_server.stop()
    xvfb.stop()
