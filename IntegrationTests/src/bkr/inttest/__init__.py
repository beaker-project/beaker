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

import pkg_resources
pkg_resources.require('SQLAlchemy >= 0.6')
pkg_resources.require('TurboGears >= 1.1')

import sys
import os
import time
import threading
import subprocess
from StringIO import StringIO
import logging, logging.config
import signal
import cherrypy
import turbogears
from turbogears import update_config
from turbogears.database import session
from bkr.server.controllers import Root
from bkr.server.util import log_to_stream

# hack to make turbogears.testutil not do dumb stuff at import time
orig_cwd = os.getcwd()
os.chdir('/tmp')
import turbogears.testutil
os.chdir(orig_cwd)

# workaround for delayed log formatting in nose
# https://groups.google.com/forum/?fromgroups=#!topic/nose-users/5uZVDfDf1ZI
orig_LogRecord = logging.LogRecord
class EagerFormattedLogRecord(orig_LogRecord):
    def __init__(self, *args, **kwargs):
        orig_LogRecord.__init__(self, *args, **kwargs)
        if self.args:
            self.msg = self.msg % self.args
            self.args = None
logging.LogRecord = EagerFormattedLogRecord

log = logging.getLogger(__name__)

CONFIG_FILE = os.environ.get('BEAKER_CONFIG_FILE', 'server-test.cfg')

def get_server_base():
    return os.environ.get('BEAKER_SERVER_BASE_URL',
        'http://localhost:%s/' % turbogears.config.get('server.socket_port'))

def with_transaction(func):
    """
    Runs the decorated function inside a transaction. Apply to setUp or other 
    methods as needed.
    """
    def _decorated(*args, **kwargs):
        with session.begin():
            func(*args, **kwargs)
    return _decorated

class DummyVirtManager(object):
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        pass
    def create_vm(self, name, lab_controllers, mac_address):
        pass
    def destroy_vm(self, name):
        pass
    def start_install(self, name, distro_tree, kernel_options, lab_controller):
        pass

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
        for i in range(40):
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
        self.popen = popen

    def run(self):
        while True:
            data = self.popen.stdout.readline()
            if not data: break
            sys.stdout.write(data)

processes = []

def setup_package():
    log.info('Loading test configuration from %s', CONFIG_FILE)
    assert os.path.exists(CONFIG_FILE), 'Config file %s must exist' % CONFIG_FILE
    update_config(configfile=CONFIG_FILE, modulename='bkr.server.config')

    # Override loaded logging config, in case we are using the server's config file
    # (we really always want our tests' logs to go to stdout, not /var/log/beaker/)
    log_to_stream(sys.stdout, level=logging.NOTSET)

    from bkr.inttest import data_setup
    if not 'BEAKER_SKIP_INIT_DB' in os.environ:
        data_setup.setup_model()
    with session.begin():
        data_setup.create_labcontroller() #always need a labcontroller
        data_setup.create_task(name=u'/distribution/install', requires=
                u'make gcc nfs-utils wget procmail redhat-lsb ntp '
                u'@development-tools @development-libs @development '
                u'@desktop-platform-devel @server-platform-devel '
                u'libxml2-python expect pyOpenSSL'.split())
        data_setup.create_task(name=u'/distribution/reservesys',
                requires=u'emacs vim-enhanced unifdef sendmail'.split())
        data_setup.create_distro()

    if not os.path.exists(turbogears.config.get('basepath.rpms')):
        os.mkdir(turbogears.config.get('basepath.rpms'))

    turbogears.testutil.make_app(Root)
    turbogears.testutil.start_server()

    if 'BEAKER_SERVER_BASE_URL' not in os.environ:
        # need to start the server ourselves
        # (this only works from the IntegrationTests dir of a Beaker checkout)
        processes.extend([
            Process('beaker', args=['../Server/start-server.py', CONFIG_FILE],
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

    turbogears.testutil.stop_server()
