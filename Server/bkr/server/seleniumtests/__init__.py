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

xvfb = None
selenium_server = None

def setup_package():
    global xvfb, selenium_server
    log.info('Spawning Xvfb ...')
    xvfb = subprocess.Popen(['Xvfb', ':4',
            '-fp', '/usr/share/X11/fonts/misc',
            '-screen', '0', '1024x768x24'])
    log.info('Xvfb spawned (pid %d)', xvfb.pid)
    log.info('Spawning selenium-server ...')
    selenium_server = subprocess.Popen(['java', '-jar',
            '/opt/selenium/selenium-server-1.0.3/selenium-server.jar',
            '-log', 'selenium.log'],
            env=dict([('DISPLAY', ':4')] + os.environ.items()))
    # wait for selenium to start up
    time.sleep(3) # TODO use a real condition here!
    log.info('selenium-server spawned (pid %d)', selenium_server.pid)

def teardown_package():
    if xvfb.poll() is not None:
        log.warning('Xvfb (pid %d) already dead, not killing', xvfb.pid)
    else:
        log.info('Sending SIGTERM to Xvfb (pid %d)', xvfb.pid)
        os.kill(xvfb.pid, signal.SIGTERM)
        xvfb.wait()
    if selenium_server.poll() is not None:
        log.warning('selenium-server (pid %d) already dead, not killing', selenium_server.pid)
    else:
        log.info('Sending SIGTERM to selenium-server (pid %d)', selenium_server.pid)
        os.kill(selenium_server.pid, signal.SIGTERM)
        selenium_server.wait()
