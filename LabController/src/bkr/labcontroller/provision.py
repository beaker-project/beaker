
import sys
import os, os.path
import errno
import logging
import time
import random
import signal
import daemon
from daemon import pidfile
from optparse import OptionParser
import pkg_resources
import subprocess
import gevent, gevent.hub, gevent.socket, gevent.event, gevent.monkey
from kobo.exceptions import ShutdownException
from bkr.log import log_to_stream, log_to_syslog
from bkr.common.helpers import SensitiveUnicode
from bkr.labcontroller.config import load_conf, get_conf
from bkr.labcontroller.proxy import ProxyHelper
from bkr.labcontroller import netboot

logger = logging.getLogger(__name__)

class CommandQueuePoller(ProxyHelper):

    def __init__(self, *args, **kwargs):
        super(CommandQueuePoller, self).__init__(*args, **kwargs)
        self.commands = {} #: dict of (id -> command info) for running commands
        self.greenlets = {} #: dict of (command id -> greenlet which is running it)

    def get_queued_commands(self):
        commands = self.hub.labcontrollers.get_queued_command_details()
        for command in commands:
            if 'power' in command and 'passwd' in command['power']:
                command['power']['passwd'] = SensitiveUnicode(command['power']['passwd'])
        return commands

    def mark_command_running(self, id):
        self.hub.labcontrollers.mark_command_running(id)

    def mark_command_completed(self, id):
        self.hub.labcontrollers.mark_command_completed(id)

    def mark_command_failed(self, id, message):
        self.hub.labcontrollers.mark_command_failed(id, message)

    def clear_running_commands(self, message):
        self.hub.labcontrollers.clear_running_commands(message)

    def poll(self):
        logger.debug('Polling for queued commands')
        for command in self.get_queued_commands():
            if command['id'] in self.commands:
                # We've already seen it, ignore
                continue
            # This command has to wait for any other existing commands against the
            # same system, to prevent collisions
            predecessors = [self.greenlets[c['id']]
                    for c in self.commands.itervalues()
                    if c['fqdn'] == command['fqdn']]
            if 'power' in command and command['power'].get('address'):
                # Also wait for other commands running against the same power address
                predecessors.extend(self.greenlets[c['id']]
                        for c in self.commands.itervalues()
                        if 'power' in c and c['power'].get('address')
                            == command['power']['address'])
            self.spawn_handler(command, predecessors)

    def spawn_handler(self, command, predecessors):
        self.commands[command['id']] = command
        greenlet = gevent.spawn(self.handle, command, predecessors)
        self.greenlets[command['id']] = greenlet
        def completion_callback(greenlet):
            if greenlet.exception:
                logger.error('Command handler %r had unhandled exception: %r',
                        greenlet, greenlet.exception)
            del self.commands[command['id']]
            del self.greenlets[command['id']]
        greenlet.link(completion_callback)

    def handle(self, command, predecessors):
        if command.get('delay'):
            # Before anything else, we need to wait for our delay period.
            # Instead of just doing time.sleep we do a timed wait on
            # shutting_down, so that our delay doesn't hold up the shutdown.
            logger.debug('Delaying %s seconds for command %s',
                    command['delay'], command['id'])
            if shutting_down.wait(timeout=command['delay']):
                return
        gevent.joinall(predecessors)
        if shutting_down.is_set():
            return
        logger.debug('Handling command %r', command)
        self.mark_command_running(command['id'])
        try:
            if command['action'] in (u'on', u'off', 'interrupt'):
                handle_power(command)
            elif command['action'] == u'reboot':
                handle_power(dict(command.items() + [('action', u'off')]))
                # This 5 second delay period is not very scientific, it's just 
                # copied from Cobbler. The idea is to give the PSU a chance to 
                # discharge, in case the power controller is returning from the 
                # 'off' command too soon.
                time.sleep(5)
                handle_power(dict(command.items() + [('action', u'on')]))
            elif command['action'] == u'clear_logs':
                handle_clear_logs(self.conf, command)
            elif command['action'] == u'configure_netboot':
                handle_configure_netboot(command)
            elif command['action'] == u'clear_netboot':
                handle_clear_netboot(command)
            else:
                raise ValueError('Unrecognised action %s' % command['action'])
                # XXX or should we just ignore it and leave it queued?
        except Exception, e:
            logger.exception('Error processing command %s', command['id'])
            self.mark_command_failed(command['id'],
                    '%s: %s' % (e.__class__.__name__, e))
        else:
            self.mark_command_completed(command['id'])
        logger.debug('Finished handling command %s', command['id'])

def find_power_script(power_type):
    customised = '/etc/beaker/power-scripts/%s' % power_type
    if os.path.exists(customised) and os.access(customised, os.X_OK):
        return customised
    resource = 'power-scripts/%s' % power_type
    if pkg_resources.resource_exists('bkr.labcontroller', resource):
        return pkg_resources.resource_filename('bkr.labcontroller', resource)
    raise ValueError('Invalid power type %r' % power_type)

def build_power_env(command):
    env = dict(os.environ)
    env['power_address'] = (command['power'].get('address') or u'').encode('utf8')
    env['power_id'] = (command['power'].get('id') or u'').encode('utf8')
    env['power_user'] = (command['power'].get('user') or u'').encode('utf8')
    env['power_pass'] = (command['power'].get('passwd') or u'').encode('utf8')
    env['power_mode'] = command['action'].encode('utf8')
    return env

def handle_clear_logs(conf, command):
    console_log = os.path.join(conf['CONSOLE_LOGS'], command['fqdn'])
    logger.debug('Truncating console log %s', console_log)
    try:
        f = open(console_log, 'r+')
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise
    else:
        f.truncate()

def handle_configure_netboot(command):
    netboot.configure_all(command['fqdn'], command['arch'],
                          command['netboot']['distro_tree_id'],
                          command['netboot']['kernel_url'],
                          command['netboot']['initrd_url'],
                          command['netboot']['kernel_options'])

def handle_clear_netboot(command):
    netboot.clear_all(command['fqdn'])

def handle_power(command):
    from bkr.labcontroller.async import MonitoredSubprocess
    script = find_power_script(command['power']['type'])
    env = build_power_env(command)
    # We try the command up to 5 times, because some power commands
    # are flakey (apparently)...
    for attempt in range(1, 6):
        if attempt > 1:
            # After the first attempt fails we do a randomised exponential
            # backoff in the style of Ethernet.
            # Instead of just doing time.sleep we do a timed wait on
            # shutting_down, so that our delay doesn't hold up the shutdown.
            delay = random.uniform(attempt, 2**attempt)
            logger.debug('Backing off %0.3f seconds for power command %s',
                    delay, command['id'])
            if shutting_down.wait(timeout=delay):
                break
        logger.debug('Launching power script %s (attempt %s) with env %r',
                script, attempt, env)
        # N.B. the timeout value used here affects daemon shutdown time,
        # make sure the init script is kept up to date!
        p = MonitoredSubprocess([script], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=300)
        logger.debug('Waiting on power script pid %s', p.pid)
        p.dead.wait()
        out = p.stdout_reader.get()
        err = p.stderr_reader.get()
        if p.returncode == 0 or shutting_down.is_set():
            break
    if p.returncode != 0:
        raise ValueError('Power script %s failed after %s attempts with exit status %s:\n%s'
                % (script, attempt, p.returncode, err[:150]))
    # TODO submit complete stdout and stderr?

def shutdown_handler(signum, frame):
    logger.info('Received signal %s, shutting down', signum)
    shutting_down.set()

def main_loop(poller=None, conf=None):
    global shutting_down
    shutting_down = gevent.event.Event()
    gevent.monkey.patch_all(thread=False)

    # define custom signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.debug('Clearing old running commands')
    poller.clear_running_commands(u'Stale command cleared on startup')

    logger.debug('Entering main provision loop')
    while True:
        try:
            poller.poll()
        except:
            logger.exception('Failed to poll for queued commands')
        if shutting_down.wait(timeout=conf.get('SLEEP_TIME', 20)):
            gevent.hub.get_hub().join() # let running greenlets terminate
            break
    logger.debug('Exited main provision loop')

def main():
    parser = OptionParser()
    parser.add_option("-c", "--config",
                      help="Full path to config file to use")
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    parser.add_option("-p", "--pid-file",
                      help="specify a pid file")
    (opts, args) = parser.parse_args()
    if opts.config:
        load_conf(opts.config)
    logging.getLogger().setLevel(logging.DEBUG)

    conf = get_conf()
    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get("PROVISION_PID_FILE", "/var/run/beaker-lab-controller/beaker-provision.pid")

    # kobo.client.HubProxy will try to log some stuff, even though we 
    # haven't configured our logging handlers yet. So we send logs to stderr 
    # temporarily here, and configure it again below.
    log_to_stream(sys.stderr, level=logging.WARNING)
    try:
        poller = CommandQueuePoller(conf=conf)
    except Exception, ex:
        sys.stderr.write('Error initializing CommandQueuePoller: %s\n' % ex)
        sys.exit(1)

    if opts.foreground:
        log_to_stream(sys.stderr, level=logging.DEBUG)
        main_loop(poller=poller, conf=conf)
    else:
        # See BZ#977269
        poller.close()
        with daemon.DaemonContext(pidfile=pidfile.TimeoutPIDLockFile(
                pid_file, acquire_timeout=0)):
            log_to_syslog('beaker-provision')
            main_loop(poller=poller, conf=conf)

if __name__ == '__main__':
    main()
