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
log = logging.getLogger('bkr.server.test.selenium.__init__')

class Process(object):
    """
    Thin wrapper around subprocess.Popen which supports starting and killing 
    the process in setup/teardown.
    """

    def __init__(self, name, args, env=None, listen_port=None):
        self.name = name
        self.args = args
        self.env = env
        self.listen_port = listen_port

    def start(self):
        log.info('Spawning %s: %s %r', self.name, ' '.join(self.args), self.env)
        env = dict(os.environ)
        if self.env:
            env.update(self.env)
        self.popen = subprocess.Popen(self.args, env=env)
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
            # with newer lsof we could just use -sTCP:LISTEN,
            # but RHEL5's lsof is too old so we have to filter for LISTEN state
            output, _ = subprocess.Popen(['/usr/sbin/lsof', '-p%d' % self.popen.pid,
                    '-iTCP:%d' % port], stdout=subprocess.PIPE).communicate()
            for line in output.splitlines():
                if '(LISTEN)' in line:
                    return
            time.sleep(1)
        raise RuntimeError('Gave up waiting for LISTEN %d' % port)

    def stop(self, signal=signal.SIGTERM):
        if not hasattr(self, 'popen'):
            log.warning('%s never started, not killing', self.name)
        elif self.popen.poll() is not None:
            log.warning('%s (pid %d) already dead, not killing', self.name, self.popen.pid)
        else:
            log.info('Sending %r to %s (pid %d)', signal, self.name, self.popen.pid)
            os.kill(self.popen.pid, signal)
            self.popen.wait()

xvfb = Process('Xvfb', args=['Xvfb', ':4', '-fp', '/usr/share/X11/fonts/misc',
        '-screen', '0', '1024x768x24'])
selenium_server = Process('selenium-server', args=['java', '-jar',
        '/opt/selenium/selenium-server-1.0.3/selenium-server.jar',
        '-log', 'selenium.log'], env={'DISPLAY': ':4'}, listen_port=4444)
beaker = Process('beaker', args=['./start-server.py', 'test.cfg'],
        listen_port=8080)

def setup_package():
    xvfb.start()
    selenium_server.start()
    beaker.start()

def teardown_package():
    beaker.stop(signal.SIGINT)
    selenium_server.stop()
    xvfb.stop()
