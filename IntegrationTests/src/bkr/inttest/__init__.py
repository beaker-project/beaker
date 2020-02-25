# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pkg_resources

pkg_resources.require('SQLAlchemy >= 0.6')
pkg_resources.require('TurboGears >= 1.1')

import sys
import os
import datetime
import time
import socket
import threading
import subprocess
import shutil
import tempfile
import re
import logging, logging.config
import signal
import unittest
import turbogears

try:
    import glanceclient.v2.client
    has_glanceclient = True
except ImportError:
    has_glanceclient = False

try:
    from keystoneauth1.identity import v3
    from keystoneauth1 import session as os_session
    has_keystoneauth1 = True
except ImportError:
    has_keystoneauth1 = False

from turbogears.database import session
from bkr.server.controllers import Root
from bkr.server.model import OpenStackRegion, ConfigItem, User, LabController, Task, Distro
from bkr.server.util import load_config
from bkr.server.tools import ipxe_image
from bkr.server.tests import data_setup
from bkr.log import log_to_stream
from bkr.inttest.mail_capture import MailCaptureThread

# hack to make turbogears.testutil not do dumb stuff at import time
orig_cwd = os.getcwd()
os.chdir('/tmp')
import turbogears.testutil

os.chdir(orig_cwd)

CONFIG_FILE = os.environ.get('BEAKER_CONFIG_FILE')


class DatabaseTestCase(unittest.TestCase):
    """
    Tests which touch the database in any way (session.begin()) should inherit
    from this, so that the session is cleaned up at the end of each test. This
    prevents ORM objects from accumulating in memory during the test run.
    """

    def __init__(self, *args, **kwargs):
        super(DatabaseTestCase, self).__init__(*args, **kwargs)
        # Putting this in __init__ instead of setUp is kind of cheating, but it
        # lets us avoid calling super() in every setUp.
        self.addCleanup(self._cleanup_session)
        # This is even more of a hack because it has nothing to do with the
        # database. But we have nowhere nicer to put this for now.
        # (We should be using pytest fixtures...)
        self.addCleanup(self._clear_captured_mails)

    def _cleanup_session(self):
        # We clear __dict__ as a kind of hack, to try and drop references to
        # ORM instances which the test has stored as attributes on itself
        # (TestCase instances are kept for the life of the test runner!)
        for name in self.__dict__.keys():
            if not name.startswith('_'):
                del self.__dict__[name]
        session.close()

    def _clear_captured_mails(self):
        mail_capture_thread.clear()


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


def fix_beakerd_repodata_perms():
    # This is ugly, but I can't come up with anything better...
    # Any tests which invoke beakerd code directly will create
    # /var/www/beaker/rpms/repodata if it doesn't already exist. But the
    # tests might be running as root (as in the dogfood task, for example)
    # so the repodata directory could end up owned by root, whereas it
    # needs to be owned by apache.
    # The hacky fix is to just delete the repodata at the end of the test, and
    # let the application (running as apache) re-create it later.
    # Call this in a tearDown or tearDownClass method.
    repodata = os.path.join(turbogears.config.get('basepath.rpms'), 'repodata')
    shutil.rmtree(repodata, ignore_errors=True)


def check_listen(port):
    """
    Returns True iff any process on the system is listening
    on the given TCP port.
    """
    # with newer lsof we could just use -sTCP:LISTEN,
    # but RHEL5's lsof is too old so we have to filter for LISTEN state ourselves
    output, error = subprocess.Popen(['lsof', '-iTCP:%d' % port],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
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
                 stop_signal=signal.SIGTERM, exec_dir=None):
        self.name = name
        self.args = args
        self.env = env
        self.listen_port = listen_port
        self.stop_signal = stop_signal
        self.exec_dir = exec_dir

    def start(self):
        _cmd_line = ' '.join(self.args)
        if self.env is None:
            log.info('Spawning %s: %r', self.name, _cmd_line)
        else:
            log.info('Spawning %s in %r: %r', self.name, self.env, _cmd_line)
        env = dict(os.environ)
        if self.env:
            env.update(self.env)
        try:
            discard_output = os.environ.get('DISCARD_SUBPROCESS_OUTPUT')
            if discard_output == '1':
                devnull = open(os.devnull, 'w')
                self.popen = subprocess.Popen(
                    self.args, stdout=devnull, stderr=devnull, env=env, cwd=self.exec_dir)
            else:
                self.popen = subprocess.Popen(
                    self.args, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, env=env, cwd=self.exec_dir)
                self.communicate_thread = CommunicateThread(popen=self.popen)
                self.communicate_thread.start()
        except:
            log.info('Failed to spawn %s', self.name)
            raise
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

    def start_output_capture(self):
        self.communicate_thread.start_capture()

    def finish_output_capture(self):
        return self.communicate_thread.finish_capture()


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
        self.capturing = False

    def run(self):
        while True:
            data = self.popen.stdout.readline()
            if not data:
                break
            if self.capturing:
                self.captured.append(data)
            else:
                sys.stdout.write(data)

    def start_capture(self):
        self.captured = []
        self.capturing = True

    def finish_capture(self):
        self.capturing = False
        result = ''.join(self.captured)
        del self.captured
        return result


slapd_config_dir = None
slapd_data_dir = None


def setup_slapd():
    global slapd_config_dir, slapd_data_dir
    slapd_config_dir = tempfile.mkdtemp(prefix='beaker-tests-slapd-config')
    slapd_data_dir = tempfile.mkdtemp(prefix='beaker-tests-slapd-data')
    log.info('Populating slapd config')
    slapadd = subprocess.Popen(['slapadd', '-F', slapd_config_dir, '-n0'],
                               stdin=subprocess.PIPE)
    slapadd.communicate("""
dn: cn=config
objectClass: olcGlobal
cn: config

dn: cn=schema,cn=config
objectClass: olcSchemaConfig
cn: schema

include: file:///etc/openldap/schema/core.ldif
include: file:///etc/openldap/schema/cosine.ldif
include: file:///etc/openldap/schema/inetorgperson.ldif
include: file:///etc/openldap/schema/nis.ldif

dn: olcDatabase=config,cn=config
objectClass: olcDatabaseConfig
olcDatabase: config
olcAccess: to * by * none

dn: olcDatabase=bdb,cn=config
objectClass: olcDatabaseConfig
objectClass: olcBdbConfig
olcDatabase: bdb
olcSuffix: dc=example,dc=invalid
olcDbDirectory: %s
olcDbIndex: objectClass eq
olcAccess: to * by * read
""" % slapd_data_dir)
    assert slapadd.returncode == 0
    log.info('Populating slapd data')
    subprocess.check_call(['slapadd', '-F', slapd_config_dir, '-n1', '-l',
                           pkg_resources.resource_filename('bkr.inttest', 'ldap-data.ldif')],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def cleanup_slapd():
    shutil.rmtree(slapd_data_dir, ignore_errors=True)
    shutil.rmtree(slapd_config_dir, ignore_errors=True)


mail_capture_thread = MailCaptureThread()


def _glance():
    # First check if we have all dependencies for runtime
    if not has_glanceclient:
        raise RuntimeError('python-glanceclient is not installed')

    if not has_keystoneauth1:
        raise RuntimeError('python-keystoneauth1 is not installed')

    # We upload the iPXE image to Glance using the same dummy credentials and
    # tenant on whose behalf we will be creating VMs later.
    username = os.environ['OPENSTACK_DUMMY_USERNAME']
    password = os.environ['OPENSTACK_DUMMY_PASSWORD']
    project_name = os.environ['OPENSTACK_DUMMY_PROJECT_NAME']
    auth_url = turbogears.config.get('openstack.identity_api_url')
    user_domain_name = os.environ.get('OPENSTACK_DUMMY_USER_DOMAIN_NAME')
    project_domain_name = os.environ.get('OPENSTACK_DUMMY_PROJECT_DOMAIN_NAME')

    auth = v3.Password(
        auth_url=auth_url,
        username=username,
        user_domain_name=user_domain_name,
        password=password,
        project_name=project_name,
        project_domain_name=project_domain_name,
    )

    sess = os_session.Session(auth=auth)
    auth_ref = auth.get_auth_ref(sess)
    glance_url = auth_ref.service_catalog.url_for(service_type='image', interface='public')

    return glanceclient.v2.client.Client(glance_url, token=auth.get_token(sess))


def setup_openstack():
    with session.begin():
        data_setup.create_openstack_region()
        session.flush()
        # Use a distinctive guest name prefix to give us a greater chance of
        # tracking instances back to the test run which created them.
        admin_user = User.by_user_name(data_setup.ADMIN_USER)
        guest_name_prefix = u'beaker-testsuite-%s-%s-' % (
            datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
            socket.gethostname())
        ConfigItem.by_name(u'guest_name_prefix').set(guest_name_prefix, user=admin_user)
        ipxe_image.upload_image(_glance(), visibility=u'private')


def cleanup_openstack():
    with session.begin():
        region = OpenStackRegion.query.one()
        log.info('Cleaning up Glance image %s', region.ipxe_image_id)
        _glance().images.delete(region.ipxe_image_id)


processes = None


def edit_file(file, old_text, new_text):
    with open(file, 'r') as f:
        contents = f.read()
    contents = re.sub(old_text, new_text, contents)
    tmp_config = tempfile.NamedTemporaryFile()
    tmp_config.write(contents)
    tmp_config.flush()
    return tmp_config


def start_process(name, env=None):
    found = False
    for p in processes:
        if name == p.name:
            p.env = env
            found = True
            p.start()
    if found is False:
        raise ValueError('%s is not a valid process name')


def stop_process(name):
    found = False
    for p in processes:
        if name == p.name:
            found = True
            p.stop()
    if found is False:
        raise ValueError('%s is not a valid process name')


def setup_package():
    assert os.path.exists(CONFIG_FILE), 'Config file %s must exist' % CONFIG_FILE
    load_config(configfile=CONFIG_FILE)
    log_to_stream(sys.stdout, level=logging.DEBUG)

    from bkr.inttest import data_setup
    if not 'BEAKER_SKIP_INIT_DB' in os.environ:
        data_setup.setup_model()
    with session.begin():
        # Fill in the bare minimum data which Beaker assumes will always be present.
        # Note that this can be called multiple times (for example, the
        # beaker-server-redhat add-on package reuses this setup function).
        if not LabController.query.count():
            data_setup.create_labcontroller()
        if not Task.query.count():
            data_setup.create_task(name=u'/distribution/check-install')
            data_setup.create_task(name=u'/distribution/reservesys',
                                   requires=u'emacs vim-enhanced unifdef sendmail'.split())
            data_setup.create_task(name=u'/distribution/utils/dummy')
            data_setup.create_task(name=u'/distribution/inventory')
        if not Distro.query.count():
            # The 'BlueShoeLinux5-5' string appears in many tests, because it's
            # the distro name used in complete-job.xml.
            data_setup.create_distro_tree(osmajor=u'BlueShoeLinux5',
                                          distro_name=u'BlueShoeLinux5-5')

    if os.path.exists(turbogears.config.get('basepath.rpms')):
        # Remove any task RPMs left behind by previous test runs
        for entry in os.listdir(turbogears.config.get('basepath.rpms')):
            shutil.rmtree(os.path.join(
                turbogears.config.get('basepath.rpms'),
                entry), ignore_errors=True)
    else:
        os.mkdir(turbogears.config.get('basepath.rpms'))

    setup_slapd()
    mail_capture_thread.start()

    if turbogears.config.get('openstack.identity_api_url'):
        setup_openstack()

    turbogears.testutil.make_app(Root)
    turbogears.testutil.start_server()

    global processes
    processes = []
    if 'BEAKER_SERVER_BASE_URL' not in os.environ:
        # need to start the server ourselves
        # Usual pkg_resources ugliness is needed to ensure gunicorn doesn't
        # import pkg_resources before we get a chance to specify our
        # requirements in bkr.server.wsgi
        processes.extend([
            Process('gunicorn', args=[sys.executable, '-c',
                                      '__requires__ = ["CherryPy < 3.0"]; import pkg_resources; '
                                      'from gunicorn.app.wsgiapp import run; run()',
                                      '--bind', ':%s' % turbogears.config.get('server.socket_port'),
                                      '--workers', '8', '--access-logfile', '-', '--preload',
                                      'bkr.server.wsgi:application'],
                    listen_port=turbogears.config.get('server.socket_port')),
        ])
    processes.extend([
        Process('slapd', args=['slapd', '-d0', '-F' + slapd_config_dir,
                               '-hldap://127.0.0.1:3899/'],
                listen_port=3899, stop_signal=signal.SIGINT),
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

    if turbogears.config.get('openstack.identity_api_url'):
        cleanup_openstack()

    mail_capture_thread.stop()
    cleanup_slapd()
